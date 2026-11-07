// Dry out an echo-y room: runs a wav through Apple's AUSoundIsolation (the ML voice isolation behind
// Final Cut's "Voice Isolation"), offline, on this Mac. Removes room reverb + background noise.
// Build:  swiftc -O voiceisolate.swift -o <scratch>/voiceisolate
// Use:    <scratch>/voiceisolate in.wav out.wav [wet%=100]
// Lower wet% (e.g. 80) blends some of the original back in if the result sounds processed.
import AVFoundation
import AudioToolbox

let args = CommandLine.arguments
guard args.count >= 3 else { print("usage: voiceisolate in.wav out.wav [wet%]"); exit(1) }
let wet = args.count > 3 ? Float(args[3]) ?? 100 : 100

let inFile = try AVAudioFile(forReading: URL(fileURLWithPath: args[1]))
let fmt = inFile.processingFormat
let engine = AVAudioEngine()
let player = AVAudioPlayerNode()
let desc = AudioComponentDescription(componentType: kAudioUnitType_Effect, componentSubType: 0x766f6973 /* 'vois' */,
                                     componentManufacturer: kAudioUnitManufacturer_Apple, componentFlags: 0, componentFlagsMask: 0)
let iso = AVAudioUnitEffect(audioComponentDescription: desc)
engine.attach(player); engine.attach(iso)
engine.connect(player, to: iso, format: fmt)
engine.connect(iso, to: engine.mainMixerNode, format: fmt)
AudioUnitSetParameter(iso.audioUnit, 0, kAudioUnitScope_Global, 0, wet, 0)       // Wet/Dry Mix
AudioUnitSetParameter(iso.audioUnit, 1, kAudioUnitScope_Global, 0, 0, 0)         // Sound to Isolate: voice

try engine.enableManualRenderingMode(.offline, format: fmt, maximumFrameCount: 4096)
try engine.start()
player.scheduleFile(inFile, at: nil)
player.play()

func render() throws {   // in a function so the output file is closed (header finalised) on return
    let outFile = try AVAudioFile(forWriting: URL(fileURLWithPath: args[2]), settings: fmt.settings)
    let buf = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: engine.manualRenderingMaximumFrameCount)!
    // the isolation model has some latency: render a little past the end, then trim the front by the same amount
    let latency = AVAudioFramePosition(iso.auAudioUnit.latency * fmt.sampleRate)
    let total = inFile.length + latency
    var written: AVAudioFramePosition = 0
    var skip = latency
    while engine.manualRenderingSampleTime < total {
        let n = AVAudioFrameCount(min(Int64(buf.frameCapacity), total - engine.manualRenderingSampleTime))
        guard try engine.renderOffline(n, to: buf) == .success else { break }
        if skip >= AVAudioFramePosition(buf.frameLength) { skip -= AVAudioFramePosition(buf.frameLength); continue }
        if skip > 0 {                                   // drop the latency frames at the start
            let keep = AVAudioFrameCount(AVAudioFramePosition(buf.frameLength) - skip)
            for c in 0..<Int(fmt.channelCount) {
                let p = buf.floatChannelData![c]
                p.update(from: p + Int(skip), count: Int(keep))
            }
            buf.frameLength = keep; skip = 0
        }
        try outFile.write(from: buf); written += AVAudioFramePosition(buf.frameLength)
    }
    print("wrote \(written) frames, latency \(latency) frames, wet \(wet)%")
}
try render()

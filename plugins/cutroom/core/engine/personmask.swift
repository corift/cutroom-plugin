// Person segmentation mask video via Apple Vision (macOS 12+). No extra installs.
// Usage: swift personmask.swift <in.mp4> <out_w> <out_h>  > raw gray8 frames on stdout
// Pipe into: ffmpeg -f rawvideo -pix_fmt gray -s WxH -r 30 -i - -c:v libx264 -crf 8 -pix_fmt yuv420p mask.mp4
// Each frame is segmented on its own, so frames run PERSONMASK_JOBS at a time (default 8) and are written in order.
import AVFoundation
import Vision
import CoreImage
import Foundation

let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
let ow = Int(args[2])!, oh = Int(args[3])!
let jobs = max(1, Int(ProcessInfo.processInfo.environment["PERSONMASK_JOBS"] ?? "") ?? 8)

let asset = AVURLAsset(url: url)
let track = asset.tracks(withMediaType: .video)[0]
let reader = try! AVAssetReader(asset: asset)
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()

let ctx = CIContext()
let stdout = FileHandle.standardOutput
let requests: [VNGeneratePersonSegmentationRequest] = (0..<jobs).map { _ in
    let req = VNGeneratePersonSegmentationRequest()
    req.qualityLevel = .accurate
    req.outputPixelFormat = kCVPixelFormatType_OneComponent8
    return req
}
var masks = [[UInt8]](repeating: [UInt8](repeating: 0, count: ow * oh), count: jobs)
var last = [UInt8](repeating: 0, count: ow * oh)
var n = 0

while true {
    var batch: [CVPixelBuffer?] = []
    while batch.count < jobs, let sb = out.copyNextSampleBuffer() { batch.append(CMSampleBufferGetImageBuffer(sb)) }
    if batch.isEmpty { break }
    var found = [Bool](repeating: false, count: batch.count)
    masks.withUnsafeMutableBufferPointer { slots in
        found.withUnsafeMutableBufferPointer { ok in
            DispatchQueue.concurrentPerform(iterations: batch.count) { i in
                guard let pb = batch[i] else { return }
                let req = requests[i]
                try? VNImageRequestHandler(cvPixelBuffer: pb, options: [:]).perform([req])
                guard let m = req.results?.first?.pixelBuffer else { return }
                var ci = CIImage(cvPixelBuffer: m)
                ci = ci.transformed(by: CGAffineTransform(scaleX: CGFloat(ow) / ci.extent.width,
                                                          y: CGFloat(oh) / ci.extent.height))
                ctx.render(ci, toBitmap: &slots[i], rowBytes: ow, bounds: CGRect(x: 0, y: 0, width: ow, height: oh),
                           format: .L8, colorSpace: nil)
                ok[i] = true
            }
        }
    }
    for i in 0..<batch.count {
        if batch[i] == nil { continue }
        if found[i] { last = masks[i] }
        last.withUnsafeBufferPointer { stdout.write(Data(buffer: $0)) }
        n += 1
        if n % 300 == 0 { FileHandle.standardError.write("mask frame \(n)\n".data(using: .utf8)!) }
    }
}
FileHandle.standardError.write("done \(n) frames\n".data(using: .utf8)!)

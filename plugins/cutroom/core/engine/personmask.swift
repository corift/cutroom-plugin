// Person segmentation mask video via Apple Vision (macOS 12+). No extra installs.
// Usage: swift personmask.swift <in.mp4> <out_w> <out_h>  > raw gray8 frames on stdout
// Pipe into: ffmpeg -f rawvideo -pix_fmt gray -s WxH -r 30 -i - -c:v libx264 -crf 8 -pix_fmt yuv420p mask.mp4
import AVFoundation
import Vision
import CoreImage
import Foundation

let args = CommandLine.arguments
let url = URL(fileURLWithPath: args[1])
let ow = Int(args[2])!, oh = Int(args[3])!

let asset = AVURLAsset(url: url)
let track = asset.tracks(withMediaType: .video)[0]
let reader = try! AVAssetReader(asset: asset)
let out = AVAssetReaderTrackOutput(track: track, outputSettings: [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA])
out.alwaysCopiesSampleData = false
reader.add(out)
reader.startReading()

let req = VNGeneratePersonSegmentationRequest()
req.qualityLevel = .accurate
req.outputPixelFormat = kCVPixelFormatType_OneComponent8
let ctx = CIContext()
let stdout = FileHandle.standardOutput
var n = 0
var buf = [UInt8](repeating: 0, count: ow * oh)

while let sb = out.copyNextSampleBuffer() {
    guard let pb = CMSampleBufferGetImageBuffer(sb) else { continue }
    let h = VNImageRequestHandler(cvPixelBuffer: pb, options: [:])
    try? h.perform([req])
    if let m = req.results?.first?.pixelBuffer {
        var ci = CIImage(cvPixelBuffer: m)
        ci = ci.transformed(by: CGAffineTransform(scaleX: CGFloat(ow) / ci.extent.width,
                                                  y: CGFloat(oh) / ci.extent.height))
        ctx.render(ci, toBitmap: &buf, rowBytes: ow, bounds: CGRect(x: 0, y: 0, width: ow, height: oh),
                   format: .L8, colorSpace: nil)
    }
    buf.withUnsafeBufferPointer { stdout.write(Data(buffer: $0)) }
    n += 1
    if n % 300 == 0 { FileHandle.standardError.write("mask frame \(n)\n".data(using: .utf8)!) }
}
FileHandle.standardError.write("done \(n) frames\n".data(using: .utf8)!)

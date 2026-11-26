import tempfile, unittest
from pathlib import Path
from PIL import Image
from encode_verify import ordered_files, overlay_mask, equal, active_checkpoint, boundary
class FrameTests(unittest.TestCase):
    def test_numeric_order_and_contiguity(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for i in range(12): (p/f"frame_{i}.png").touch()
            self.assertEqual([int(f.stem.split("_")[1]) for f in ordered_files(p,12)],list(range(12)))
            (p/"frame_3.png").unlink()
            (p/"frame_03.png").touch()
            (p/"frame_003.png").touch()
            with self.assertRaises(ValueError): ordered_files(p,12)
    def test_exact_timing(self):
        self.assertEqual(sum(boundary(i+1)-boundary(i) for i in range(144)),6000)
        self.assertIsNone(active_checkpoint(12))
        self.assertEqual([active_checkpoint(i) for i in [22,43,65]],[0,1,2])
        self.assertTrue(all(active_checkpoint(i) is None for i in range(77,144)))
    def test_overlay_accepts_only_opaque_allowed_pixels(self):
        base=Image.new("RGBA",(5,5),(0,0,0,0))
        base.putpixel((2,2),(49,91,205,255))
        overlay=Image.new("RGBA",base.size)
        self.assertTrue(equal(base,overlay_mask(base,overlay,None,(17,24,39))))
        overlay.putpixel((2,2),(255,255,255,255))
        self.assertEqual(overlay_mask(base,overlay,(1,1,4,4),(17,24,39)).getpixel((2,2)),(17,24,39,255))
        with self.assertRaises(ValueError): overlay_mask(base,overlay,None,(17,24,39))
        with self.assertRaises(ValueError): overlay_mask(base,overlay,(0,0,1,1),(17,24,39))
        overlay.putpixel((1,1),(255,255,255,255))
        with self.assertRaises(ValueError): overlay_mask(base,overlay,(1,1,4,4),(17,24,39))
        overlay.putpixel((1,1),(0,0,0,0))
        overlay.putpixel((2,2),(255,0,0,255))
        with self.assertRaises(ValueError): overlay_mask(base,overlay,(1,1,4,4),(17,24,39))
    def test_mask_uses_exact_palette_and_preserves_alpha(self):
        base=Image.new("RGBA",(3,3),(49,91,205,255))
        mask=Image.new("RGBA",base.size)
        mask.putpixel((1,1),(255,255,255,128))
        result=overlay_mask(base,mask,(0,0,3,3),(17,24,39))
        expected=Image.alpha_composite(base,Image.new("RGBA",base.size,(17,24,39,128)))
        self.assertEqual(result.getpixel((1,1)),expected.getpixel((1,1)))
        self.assertEqual(result.getpixel((0,0)),base.getpixel((0,0)))
        self.assertEqual(result.getchannel("A").tobytes(),base.getchannel("A").tobytes())
        mask.putpixel((1,1),(240,240,240,255))
        with self.assertRaises(ValueError): overlay_mask(base,mask,(0,0,3,3),(17,24,39))
if __name__=="__main__": unittest.main()

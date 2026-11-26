import unittest
from prepare import validate_canvas, git_show
from geometry import crop_svg, VIEWBOX, xy, checkpoint_boxes
ROOT = "brand-identity/08-review/circuit-industrial-v2/"
BG = '<rect width="1448" height="1086" fill="#F3F6FC"/>'
DIV = '<rect id="divider" x="220" y="768" width="1008" height="12" fill="#315BCD"/>'
class CanvasTests(unittest.TestCase):
    def test_exact_dark_and_light_derivative(self):
        validate_canvas(git_show(ROOT+"vib-lockup.svg").decode())
        validate_canvas(git_show(ROOT+"vib-lockup-light.svg").decode().replace(BG,"",1))
    def test_opaque_background_rejected(self):
        with self.assertRaises(ValueError):
            validate_canvas(git_show(ROOT+"vib-lockup-light.svg").decode())
    def test_divider_change_rejected(self):
        svg=git_show(ROOT+"vib-lockup.svg").decode()
        for replacement in ("", DIV.replace('width="1008"','width="1009"'), DIV+BG):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                validate_canvas(svg.replace(DIV,replacement,1))
    def test_only_viewbox_changes(self):
        svg=git_show(ROOT+"vib-lockup.svg").decode()
        result=crop_svg(svg)
        self.assertEqual(result.replace(f'viewBox="{VIEWBOX}"','viewBox="0 0 1448 1086"',1),svg)
        with self.assertRaises(ValueError): crop_svg(result)
        for (x,y),(l,t,r,b) in zip(((344,508),(700,428),(1104,508)),checkpoint_boxes()):
            px,py=xy(x+52,y+52)
            self.assertTrue(l<px<r and t<py<b)
if __name__ == "__main__": unittest.main()

# Experimental motion design
Use exact original outlined artwork and Cobalt Precision: Midnight #111827, Cobalt #315BCD, Steel Blue #879BC4, Ice White #F3F6FC. No gradients, glow, text reconstruction, decorative circuitry or geometry changes. Dark accent Steel Blue; light accent Midnight for contrast. Only checkpoint rims temporarily change color. Timeline 0.5–1.4 / 1.4–2.3 / 2.3–3.2 seconds; hold original through 6s. One finite GSAP timeline, infinite loop in WebP. This file is not a new brand lock.

Render original reference and temporary accent layers separately to avoid browser compositing changes to the original artwork. Validate raw overlay alpha, active checkpoint and color before compositing into complete RGBA frames. This is a rendering implementation change, not a design change.

White is used solely as an internal opacity-mask channel, never as an additional output palette color. The compositor applies the selected approved accent RGB.

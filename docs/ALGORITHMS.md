# Rendering Algorithms & Mathematical Derivations

`ascii-motion` computes every transformation directly from mathematical first principles and computer vision fundamentals without precomputed hardcoded tables.

---

## 1. Aspect Ratio Correction & Character Cell Geometry

Standard monospace terminal characters are rectangular rather than square, typically featuring a width-to-height ratio ($\rho_{\text{char}}$) of approximately $0.5$ (e.g., 8 pixels wide by 16 pixels high).

A naive pixel downsampling that scales an image to $W$ character columns by $H = W / (\text{DAR})$ rows stretches recognizable objects vertically by $2\times$ because each cell occupies twice as much vertical space as horizontal space.

To preserve the geometric display aspect ratio ($\text{DAR} = W_{\text{src}} / H_{\text{src}}$), the target row count $H$ is calculated as:

$$H = \max\left(1, \left\lfloor \frac{W}{\text{DAR}} \times \rho_{\text{char}} + 0.5 \right\rfloor\right)$$

Where $\rho_{\text{char}} \in [0.45, 0.55]$ (configurable via `char_aspect_ratio`, defaulting to $0.5$).

---

## 2. Perceptually Weighted Luminance

Human visual perception is non-uniformly sensitive to spectral wavelengths, exhibiting peak sensitivity to green light, moderate sensitivity to red, and minimal sensitivity to blue.

`ascii-motion` uses the standard ITU-R BT.709 (sRGB/HDTV) colorimetric coefficients:

$$Y = 0.2126 \cdot R + 0.7152 \cdot G + 0.0722 \cdot B$$

For legacy broadcast sources, the ITU-R BT.601 standard is also supported:

$$Y = 0.2990 \cdot R + 0.5870 \cdot G + 0.1140 \cdot B$$

---

## 3. Tone Mapping & Gamma Transformations

Luminance values $Y \in [0.0, 1.0]$ undergo tone adjustments:

1. **Brightness scaling**:
   $$Y_1 = \min(1.0, Y \times \beta)$$
2. **Contrast centering**:
   $$Y_2 = \text{clip}\left((Y_1 - 0.5) \times \gamma_{\text{contrast}} + 0.5, 0.0, 1.0\right)$$
3. **Gamma transfer**:
   $$Y_3 = Y_2^{1 / \gamma_{\text{exp}}}$$
4. **Inversion**:
   $$Y_{\text{final}} = 1.0 - Y_3 \quad (\text{if inverted})$$

---

## 4. Recursive Bayer Matrix Generation

Rather than hardcoding static dither tables, Bayer ordered dither matrices are generated dynamically from recursive tensor algebra.

Starting from the base matrix:

$$M_0 = \begin{bmatrix} 0 \end{bmatrix}$$

The matrix of order $k+1$ is derived from order $k$:

$$M_{k+1} = \frac{1}{4} \begin{bmatrix} 4 M_k & 4 M_k + 2 \\ 4 M_k + 3 & 4 M_k + 1 \end{bmatrix}$$

Order 1 yields a $2 \times 2$ matrix, Order 2 yields $4 \times 4$ (16 discrete levels), and Order 3 yields $8 \times 8$ (64 levels). The matrix is tiled across the image grid and modulates the quantization threshold.

---

## 5. Vectorized Sobel Convolution & Edge Strokes

Horizontal and vertical image gradients are computed using the Sobel operators:

$$K_x = \begin{bmatrix} -1 & 0 & 1 \\ -2 & 0 & 2 \\ -1 & 0 & 1 \end{bmatrix}, \quad K_y = \begin{bmatrix} -1 & -2 & -1 \\ 0 & 0 & 0 \\ 1 & 2 & 1 \end{bmatrix}$$

To achieve maximum performance without external dependencies, convolution is evaluated using vectorized NumPy array slicing:

$$\nabla_x[1:-1, 1:-1] = \frac{(I[:-2, 2:] + 2 I[1:-1, 2:] + I[2:, 2:]) - (I[:-2, :-2] + 2 I[1:-1, :-2] + I[2:, :-2])}{4}$$

$$\nabla_y[1:-1, 1:-1] = \frac{(I[2:, :-2] + 2 I[2:, 1:-1] + I[2:, 2:]) - (I[:-2, :-2] + 2 I[:-2, 1:-1] + I[:-2, 2:])}{4}$$

Gradient magnitude $G = \sqrt{\nabla_x^2 + \nabla_y^2}$ enhances outlines. Gradient angle $\theta = \arctan2(\nabla_y, \nabla_x)$ maps strong edges to directional strokes:
- $\theta \approx 0^\circ$ or $180^\circ \implies \text{'-'}$
- $\theta \approx 45^\circ \implies \text{'/'}$
- $\theta \approx 90^\circ \implies \text{'\|'}$
- $\theta \approx 135^\circ \implies \text{'\\'}`

---

## 6. Adaptive Temporal Stabilization

Successive frames in compressed video often exhibit sensor noise or micro-variations that cause high-frequency ASCII character flickering in static backgrounds.

Temporal smoothing applies an exponential moving average with motion-decay dampening:

$$\Delta = |Y_t - Y_{t-1}|$$

$$m = \text{clip}\left(\frac{\Delta}{\tau_{\text{motion}}}, 0.0, 1.0\right)$$

$$\alpha_{\text{eff}} = \alpha \times (1.0 - m)$$

$$Y_t^{\text{stable}} = (1.0 - \alpha_{\text{eff}}) Y_t + \alpha_{\text{eff}} Y_{t-1}$$

Where $\tau_{\text{motion}}$ is the motion sensitivity threshold. In static regions ($\Delta \to 0$), $\alpha_{\text{eff}} = \alpha$, smoothing out noise. When rapid object movement occurs ($\Delta > \tau_{\text{motion}}$), $\alpha_{\text{eff}} \to 0$, preventing motion blur or trails.

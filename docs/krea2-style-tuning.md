# 画风调校：Krea 2 从「AI 味」到「三渲二」

> 目标画风：「写实二次元 / 游戏引擎渲染感」：人物轮廓清晰、阴影有硬边、材质接近 PBR、但脸仍是二次元比例。

## 一、走过的七个方向

| # | 方向 | 关键锚点 | 结果 |
| --- | --- | --- | --- |
| 1 | 普通描述 | — | 像两年前的 AI 图，不像正经插画 |
| 2 | 有主张的提示词 | 光源方向、暗部、构图 | 有效，但小模型的 ceiling 在「平均正确」 |
| 3 | 换 Krea 2 | — | 明显好一截 |
| 4 | anime 风格 LoRA | `anime illustration` | 全部跑向「番剧手绘」，方向反了 |
| 5 | 半写实 | `semi-realistic, subsurface scattering` | 变成真人，脸不像二次元 |
| 6 | 写实二次元 | `2.5D anime, anime character design` | 接近（约六七成），材质与光影不够 |
| 7 | **三渲二（最终方向）** | `toon-shaded 3D, cel-shaded shadows, clear outline, anime facial proportions` | 阴影硬边、有描边、五官扁平，最接近目标 |

## 二、五条教训

1. 🔴 **负向里绝不能写 `3d render`** —— 早期每版都写了，等于一直在把「游戏引擎渲染感」往外推。
2. 🔴 **`semi-realistic` 会把人推向真人** —— 要二次元的脸，必须显式写 `anime facial proportions / large eyes / stylized features`。
3. 🔴 **`illustration / painterly` 会把手绘感拉满** —— 想要 3D 质感就不能用这两个词当主锚。
4. ✅ **三渲二的三个开关**：`hard-edged cel-shaded shadows`（硬边块状阴影）+ `clear dark outline strokes`（描边）+ `flat-shaded face / minimal stylized nose and lips`（五官扁平化）。
5. ⚠️ **Krea 2 的天然倾向是写实** —— 不显式压卡通化，它一定给你偏真人的 3D。

## 三、当前最佳参数（style reference 链路）

| 项 | 值 |
| --- | --- |
| 底模 | Krea 2 Turbo（int8 版） |
| 文本编码器 | Qwen3-VL 4B（type=`krea2`） |
| VAE | qwen_image_vae |
| LoRA | `krea2_style_reference.safetensors`，强度 1.0 |
| 参考图 | 1 张，优先选色调与材质最接近目标的 |
| 尺寸 | 2048×1152 或 2560×1440 |
| 步数 / cfg | 8 / 1.0 |

## 四、备用方案 A：2D 插画载体 + 物理级光照

有时「三渲二」不是目标，要的是「看起来像手绘、但光符合物理」。这套参数被验收过「不难看」，存下来当备用。

核心骨架：

```
2D anime illustration with physically accurate global illumination and material response.
painterly 2D art, but every light behaviour follows physics:
subsurface scattering making the skin translucent along the terminator,
cream-white diffuse highlights, cool teal and violet shadowed skin,
anisotropic angel-ring highlights on hair strands, roughness variation on
leather versus metal, sharp pinpoint speculars on buckles, soft broad speculars on fabric.
Strong contrast, shallow depth of field.
```

参数：Krea 2 Turbo int8 + style reference LoRA（1.0），参考图 1 张，8 步 / cfg 1.0，2048×1152 或 1152×2048。

## 五、还没验证的方向

1. **纯 2D 商业插画路线** —— 如果目标其实是「商业手绘键艺术图」而不是游戏截图，需要另一套锚点（`commercial anime key art, graphic composition`），不能用三渲二。
2. **专门训一个风格 LoRA** —— 环境能搭，但 12.8B 级模型在 32 GB 内存上加载就爆（见 [`experiment-log.md`](experiment-log.md) E8）。换更大内存的机器后可以直接用。

## 六、判断「像不像」的可操作口径

别争「赛璐璐/厚涂」这种词，看三个可指认项：

- **阴影边**：是否成块、块边缘是否锐利；
- **描边**：人物外轮廓是否有深色描边、是否均匀；
- **脸的比例**：眼占比、鼻口简化程度。

三个都对，才叫「到了」；只对两个就是方向偏了。

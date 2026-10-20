# Krea 2 Identity Edit：实测与边界

> 目标：用一张立绘把角色「演绎」到新的姿势与场景里，并且保持身份。
> 结论先放：**这条链做不到。它只会复制源图，不会演绎。**

## 一、它是什么

`Krea 2 Identity Edit` 是一个社区 LoRA + 自定义节点组成的链路。工作方式是把源图的 latent 直接当模型的 frame 0 塞进采样，再用 ref_boost 控制「参考强度」。

因为源图 latent 就在采样起点，它天然偏向「沿原图重画」，而不是「理解角色后重画到新构图」。

## 二、链路（API 格式）

```
UNETLoader(krea2_turbo_int8_convrot)
  → LoraLoaderModelOnly(krea2_identity_edit_v2 @1.0)
    → Krea2EditModelPatch.model

LoadImage(source) → VAEEncode → patch.source_latent
LoadImage(source) → patch.source_image（像素路径，必接）
EmptySD3LatentImage → patch.target_latent（必接，否则 source 在采样中重复编码）
EmptySD3LatentImage → KSampler.latent_image

Krea2EditGroundedEncode(clip, prompt, image) → KSampler.positive
Krea2EditGroundedEncode(clip, "", image)     → KSampler.negative（cfg=1 时空转，但必须接）

KSampler: euler / simple / denoise 1.0
```

两图模式：场景图走主输入，人物走 `_b` 三个口。训练顺序是 scene → subject。

## 三、官方参数口径

- **Turbo：10 步、cfg 1**。8 步构图遵循更强，12 步脸部细节更多，10 步平衡。
- **ref_boost：4.0 推荐**；>10 开始过度复制（removals/replacements 会失败）；<1 抑制参考。
- **grounding_px**：训练范围 384–768；低 = 编辑遵循强，高 = 身份保真强；人物建议 1024。
- **生成 ≤ 2 MP**，1 MP 是甜点。
- 移除类编辑要 RAW 模型 + CFG 3–4 + 20 步；Turbo@cfg1 会重画而不是删除。
- fit_mode：`fit` = 按目标尺寸重采样，`crop` = 老权重兼容。

## 四、实测数据（16 GB / int8 turbo）

| 模式 | 参数 | 尺寸/步数 | 耗时 | 结果 |
| --- | --- | --- | --- | --- |
| 单图，白底立绘 → 废墟全身 | ref_boost 4 | 1024×1536 / 10 | 115 s | 脸没保住 |
| 单图，只换背景 | ref_boost 4 / 8 | 1024×1024 / 10 | 85 / 81 s | 脸 3.5 → 4.7 / 5 |
| 单图重摆 | ref_boost 8 | 1024×1536 / 10 | 103 s | 脸 5/5，但人物像「贴上去的」 |
| 两图：场景 + 人物 | ref_boost 4 / 2 | 1024×1536 / 10 | 137 / 135 s | 仍判五项问题（几何/光影/接触阴影/手/比例） |
| 最小编辑（只改裙子颜色） | ref_boost 4 | 1024×1024 / 10 | 54 s | 裙子改对了，**但全图被重绘**（色温/背景/护甲细节全变） |

## 五、五条结论

1. **没有 mask，全程全图重采样。** 连「只改裙子颜色」都会把背景与整体色温重绘。想保背景必须另加 inpaint mask。
2. **ref_boost 是真有用的旋钮**，但它和「新姿势」互相矛盾：4 → 8 脸更像，8 已经过度复制（人物几乎原样贴进新构图）。
3. **白底立绘不适合当被编辑的源图**：`fit` 会把白底也当内容喂进去，模型没有背景可依只能编。
4. **两图模式方向对，融合质量一般**：光影方向不统一、接触阴影缺失、手部畸变。
5. **速度参考**：1024² 单图 54–85 s；1024×1536 单图 100–115 s；两图约 137 s。

## 六、社区参数对照（也救不了）

社区教程给了一套不同参数：**cfg 2.5、12 步、提示词 KEEP-first、负向加 `diptych, split screen, two panels, side by side`**（因为模型爱自己生成并排对比图）。

按这套跑（12 步 cfg 2.5）：**结果与 cfg1 版无实质差异** —— 背景仍崩、人物仍复制。

⇒ **这不是参数没调对，是工具类别不对。**

## 七、唯一能用的方式：把它当渲染器

如果一定要用这条链，正确位置是「二次渲染」而不是「生成」：

```
先用普通底模出底图（构图、姿势、场景都定好）
  → 再用 Krea 2 低 denoise img2img 重绘（提升材质与光影）
  → SetLatentNoiseMask 捂住脸与头发（低 denoise 下每步都会把脸往自己的先验拉）
```

实测 denoise：0.30 保结构、0.40 可用、**0.50 直接换头**。

## 八、一句话选型

| 需求 | 选什么 |
| --- | --- |
| 换场景/姿势还要认得出 | Qwen-Image-Edit 系（零样本，1–3 张参考图） |
| 要 1:1 复刻 | 训角色 LoRA |
| 只提升材质/光影 | 低 denoise img2img + 分区 mask |
| 换背景 | 需要 inpaint mask，不能靠 Identity Edit |

# 材质与光影：把「高级感」拆成可写的参数

> 问题：同一套提示词习惯，出来的图总是「一种肤色、一样亮」——不脏也不崩，但就是不像一张正经插画。
> 本文把这种差距拆成可以写进提示词的具体项，每项都带一个可检查的判据。

## 一、皮肤：三层冷暖（最关键的差距）

多数提示词只写 `subsurface scattering on skin`，太笼统。模型不会自己分配冷暖，它会把整张脸的皮肤写成一个颜色。

真实皮肤在同一光源下有三层：

| 层级 | 颜色走向 | 出现在哪 |
| --- | --- | --- |
| 亮部 | 暖白 → 极淡奶油 | 主光直射 |
| 明暗交界线 | **高饱和暖红/橙（透光带）** | 背光或侧光的薄处：耳廓、鼻尖、指缝、大腿边缘 |
| 暗部 | **冷青 / 紫罗兰**（不压黑） | 环境反弹光 |

可直接用的写法：

```
subsurface scattering on skin with warm red translucency along the light-shadow border,
cream-white highlights, cool violet and teal shadows (no pure black),
skin with visible color temperature gradient from warm highlights to cool shadows
```

**判据**：只看一个点——暗部是不是纯黑。是纯黑就说明冷暖分层没生效。

## 二、光影：硬边切块 ＋ 强反弹光

| 要素 | 做法 |
| --- | --- |
| 主光 | 顶侧逆光（左上/右上偏后），模拟舞台聚光 |
| 阴影边缘 | **硬边切块**（cast shadow 锐利），块**内部**柔和过渡 |
| 反弹光 | 极强，背景色（青蓝/绿）映到人物暗部边缘 |
| 轮廓光 | 头发/肩/腿外侧有青绿+暖白交织的 rim light |

```
top-side backlight, hard-edged cast shadows with soft internal gradients,
strong teal bounce light from the environment wrapping the shadow edges,
rim light tracing the silhouette
```

**判据**：把阴影边剪出来放大。全软 = 光没分层；全硬 = 像贴纸。要的是「块边缘硬、块内部软」。

## 三、五种材质，五组高光

这是「区分度」的真正来源。高级感不是画得细，是**同一光源下每种材质给出不同形态的高光**。全部一样亮、一样软，就会糊成一层塑料。

| 材质 | 高光形态 | 反光强度 | 暗部 | 提示词锚点 |
| --- | --- | --- | --- | --- |
| 皮肤 | 极弱、大面积漫反射 | 哑光 | 冷青紫 | `matte subsurface skin, soft diffuse highlight` |
| 头发 | **线状 / 天使环** | 强但边缘柔 | 冷青 | `anisotropic strand highlights, angel-ring hair sheen` |
| 皮革 / 弹性布料 | 粗糙漫反射，高光面积大 | 中低 | 带环境色 | `rough leather, broad soft specular` |
| 金属 / 硬质 | **极小极亮的点高光** | 极高，反射环境 | 极深带环境色 | `sharp pinpoint specular on brushed metal, environment reflection` |
| 橡胶 / 绑带 | 哑光，几乎无高光 | 极低 | 深且带色 | `matte rubber straps, no specular` |

**判据**：蒙住颜色只看亮度分布。如果所有材质的亮部形状差不多，就是没分材质。

## 四、色彩：青橙互补，暗部带色

- 色板：**Teal & Orange**（环境青绿 + 人物暖白/肉红/亮黄）。
- 饱和度：高，但不脏——靠明度差拉开，不靠提高饱和。
- 暗部：**绝不纯黑**，一定带色（深蓝紫 / 闷青）。
- 对比：高。

```
teal and orange color grading, high contrast, shadows tinted deep indigo and teal (never pure black),
vivid but clean saturation
```

## 五、后期三件

| 效果 | 提示词 |
| --- | --- |
| 高光溢出 | `bloom on highlights, soft glow around bright edges` |
| 胶片颗粒 | `subtle film grain, fine noise texture` |
| 景深 | `very shallow depth of field, foreground bokeh` |

⚠️ 景深词必须带作用对象。光禿禿一句 `shallow depth of field` 会把整张画都糊掉。

## 六、可直接套的三段式模板

```
[光] top-side backlight with hard-edged cast shadows and strong teal bounce light
[材质] matte subsurface skin with warm translucency at the terminator; anisotropic hair sheen;
       rough leather with broad specular; sharp pinpoint specular on metal; matte rubber straps
[色/后期] teal and orange grading, shadows tinted deep indigo, bloom on highlights, shallow DOF on the face
```

## 七、为什么这些参数有效（机制）

- 模型对「材质」的理解是**高光统计**，不是物理材质名。写 `rough leather` 不如写高光形态有效。
- 冷暖分层本质是告诉模型「不要用一个色】，它必须依赖分段描述才会分开。
- 硬边阴影对应一个很强的先验（舞台光/棚拍），软阴影则默认向「照片/渲染器的均匀光」靠。

## 八、已知边界

- 皮肤透光带写得过强会变「塑料红光」，先从中等强度试。
- 头发天使环在各向异性渲染里是真实效应，但低分辨率下会消失；先出 1024 以上再判。
- 以上均为提示词层。底模本身对材质的理解不够时，参数堆到死也拉不回来——那时候要换模型或加材质 LoRA。

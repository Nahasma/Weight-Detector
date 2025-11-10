# AI物品识别系统（MVP/终版增强）

这是一个基于 SiliconFlow 多模态大模型的网页应用。用户上传图片后，系统识别图片中的主要物品并返回物品名称与估算重量（公斤）。支持在前端配置 API 密钥、选择不同的 Qwen 模型，以及后端自动容错切换到其他模型。

## 技术栈

- 后端：`Python (Flask)`、`flask-cors`、`python-dotenv`
- 前端：`HTML` + `原生 JavaScript`
- AI 服务：`SiliconFlow API`（Qwen 家族视觉/多模态模型）

## 目录结构

```
detector/
├── backend/
│   ├── app.py              # Flask 服务与接口
│   ├── requirements.txt    # 后端依赖
│   └── .env                # 环境变量（SILICONFLOW_API_KEY）
├── frontend/
│   └── index.html          # 前端页面与脚本
├── sample/                 # 示例图片
└── README.md               # 本说明文档
```

## 功能概览

- 图片识别：上传 `jpg/png` 图片，返回物品名称与估算重量。
- API 密钥配置：前端输入并一键保存到后端环境变量（`.env`）。
- 模型选择：前端下拉框选择以下模型，并在后端自动容错切换。
  - `Qwen/Qwen3-VL-32B-Instruct`
  - `Qwen/Qwen3-VL-32B-Thinking`
  - `Qwen/Qwen3-VL-8B-Instruct`
  - `Qwen/Qwen3-VL-8B-Thinking`
  - `Qwen/Qwen3-VL-235B-A22B-Instruct`
  - `Qwen/Qwen3-VL-235B-A22B-Thinking`
  - `Qwen/Qwen3-Omni-30B-A3B-Instruct`
  - `Qwen/Qwen3-Omni-30B-A3B-Thinking`
- 容错机制：若所选模型调用失败，后端会自动尝试其他模型；返回结果中附带 `used_model`。

## 快速开始

### 环境要求

- `Python 3.10+`
- 可访问互联网（调用 `https://api.siliconflow.cn`）

### 安装依赖

1) 进入项目根目录并安装后端依赖：

```powershell
cd backend
pip install -r requirements.txt
```

如果你遇到 `Client.__init__() got an unexpected keyword argument 'proxies'`，本项目已固定 `httpx==0.27.0` 以规避该兼容性问题；如仍出现，执行：

```powershell
pip install -r requirements.txt --upgrade --force-reinstall
```

### 启动后端服务

从项目根目录运行：

```powershell
python backend/app.py
```

后端默认监听 `http://127.0.0.1:5001/`。

### 启动前端页面

使用任意静态文件服务器（示例为 Python 内置）：

```powershell
cd frontend
python -m http.server 5500
```

在浏览器访问 `http://localhost:5500/index.html`。

## 用户操作流程（详细）

1) 配置 API 密钥
   - 打开前端页面顶部“API Key 配置”区域。
   - 在输入框中填入你的 `SILICONFLOW_API_KEY`，点击“确定配置”。
   - 成功后会显示脱敏后的密钥状态，如 `sk-12...abcd`。
   - 你也可以手动编辑 `backend/.env` 文件：
     ```
     SILICONFLOW_API_KEY=sk-你的真实密钥
     ```

2) 选择模型
   - 在“选择AI模型”下拉框中选择目标模型（默认使用列表第一项）。

3) 上传图片并识别
   - 点击“Upload an Image”，选择 `jpg/png` 图片。
   - 点击“Recognize Item”发起识别请求。
   - 前端将通过 `POST /recognize` 上传图片和你所选模型，后端会：
     - 尝试该模型；失败时自动切换至备选模型。
     - 返回 JSON 结果，并附带 `used_model`（后端实际使用的模型）。

4) 查看结果
   - 页面将显示识别出的物品名称 `item_name` 与估算重量 `estimated_weight_kg`（单位：kg）。

## 接口说明

- `POST /recognize`
  - 表单字段：`file`（图片文件），`model`（可选，模型名）。
  - 返回：
    ```json
    {
      "item_name": "Red Apple",
      "estimated_weight_kg": 0.15,
      "used_model": "Qwen/Qwen3-VL-32B-Instruct"
    }
    ```
- `GET /config`
  - 返回当前密钥是否已配置与脱敏密钥：
    ```json
    { "configured": true, "masked_key": "sk-12...abcd" }
    ```
- `POST /config`
  - 请求体：`{"api_key": "sk-..."}`
  - 作用：写入并更新 `backend/.env` 的 `SILICONFLOW_API_KEY`。

## 故障排除

- 报错 `AI API Error: Client.__init__() got an unexpected keyword argument 'proxies'`
  - 说明：`openai==1.3.0` 与较新的 `httpx` 版本不兼容。
  - 处理：本项目已在 `requirements.txt` 固定 `httpx==0.27.0`；若仍异常，执行：
    - `pip install -r backend/requirements.txt --upgrade --force-reinstall`
    - 确认你的 Python 环境未混用多个包管理器（如 Anaconda 与系统 Python）。

- 提示未配置 API 密钥
  - 在前端页面顶部配置密钥，或手动编辑 `backend/.env`。
  - 重试识别请求。

- 图片格式不支持
  - 当前仅支持 `JPEG/PNG`。

- CORS 或跨域问题
  - 后端已启用 `flask-cors`，若仍有问题，确保前后端地址端口正确（`http://127.0.0.1:5001` 与 `http://localhost:5500`）。

## 使用技巧与注意事项

- 图片尽量清晰且主体居中，可提升识别稳定性。
- 当模型频繁超时或返回格式不正确，尝试切换到其他模型。
- 如果需要在结果区域显示后端实际使用的模型，可在前端增加对 `used_model` 的展示。
- 生产环境请勿暴露密钥；前端配置仅用于本地开发与演示。

## 许可证

本项目基于“AI物品识别系统”MVP 指南实现，示例代码仅用于学习与演示。
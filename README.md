# PikPakApi

PikPak API Python 实现

# Install

pip3 install pikpakapi


### 登陆验证码

如果遇到如下提示：

```bash
Please solve the captcha in the browser: https://user.mypikpak.com/captcha/v2/spritePuzzle.html?action=POST%3A%2Fv1%2Fauth%2Fsignin&appName=NONE&appid=XBASE&captcha_token=ck0.xxxxx&clientVersion=NONE&client_id=YUMx5nI8ZU8Ap8pm&creditkey=ck0.xxxx&credittype=1&device_id=20af2b71ef854c3db2780c8d3c192f9a&deviceid=20af2b71ef854c3db2780c8d3c192f9a&event=login3&mainHost=user.mypikpak.com&platformVersion=NONE&privateStyle=&traceid=&redirect_uri=https%3A%2F%2Fmypikpak.com%2Floading&state=getcaptcha1716395788716
Input the captcha_token (from the browser address bar, it's after captcha_token=):
```

将提示中的链接复制粘贴到浏览器，通过滑块验证码之后，在浏览器地址栏找到 `captcha_token` 参数到值，复制粘贴到程序中，注意不要复制错误。

例如：
```bash
https://mypikpak.com/loading?state=getcaptcha1716395599394&captcha_token=ck0.aBc6jFSxbI4qhXVsAh8jQps_mcYLRfYfu9YXv2rOaai_7MRWnKpc0MUtyOBpCo68bh_pCcBg3-GK-FCB3DYIBSBn3e1ywEkRWz4g56R3dH7UcUTs9QZGacSd3NStECx_8MG2bHZpBwmuuQVBsXokCR42uHssss_IrjfKH5nzODrgXWXJpccc9gtwJ97G7oVseuLSyGUNvMRuOoCquczH_u3b10An1vW0eHMvj_YQCg9LpFC_RW_ZXU2-DwhCjEUDfLC-x-LBLxxApk7huSFXk-pwEOcGbWnq8J-T56KCvrxJTjgYgezEVAJzVRGuH5TKY-jqJKoMR3MkVxszInM&expires_in=549
```
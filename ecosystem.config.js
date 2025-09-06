module.exports = {
  apps: [
    {
      name: "scrapling-api",
      script: "O:\\.pyenv\\pyenv-win\\versions\\3.10.8\\python.exe",
      args: "-m uvicorn app.main:app --host 0.0.0.0 --port 5680",
      interpreter: "none",
      cwd: __dirname,
      autorestart: true,
    },
  ],
};

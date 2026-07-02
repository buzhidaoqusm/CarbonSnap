``` commands
ssh <UCD_USERNAME>@<RDP_HOST>
ssh student@<VM_HOST>
<VM_PASSWORD>

cd ~/CarbonSnap/
git pull

<GITHUB_USERNAME>
<GITHUB_TOKEN>

cd frontend
npm ci
npm run build

cd ../backend
source .venv/bin/activate
pip install -r requirements.txt
flask --app run.py db upgrade

sudo systemctl daemon-reload
sudo systemctl restart gunicorn.service
sudo nginx -t
sudo systemctl reload nginx

https://<VM_HOST>/
```
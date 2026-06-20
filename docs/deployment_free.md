# Deployment Guide — JobFit AI

Tài liệu này hướng dẫn deploy JobFit AI miễn phí bằng:

- **Vercel Free** cho frontend Next.js
- **Render Free** cho backend FastAPI
- **Render PostgreSQL Free** cho database PostgreSQL/pgvector

Repo hiện có:

```text
frontend/                 Next.js 14 app
backend/                  FastAPI app + Alembic migrations
infra/docker/             Dockerfiles
render.yaml               Render Blueprint cho backend + database
```

## 1. Kiến trúc deploy

```text
User Browser
  |
  v
Vercel Frontend
  |
  | NEXT_PUBLIC_API_BASE_URL
  v
Render Backend FastAPI
  |
  | DATABASE_URL / SYNC_DATABASE_URL
  v
Render PostgreSQL + pgvector
```

Frontend gọi backend qua biến môi trường:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

Backend chỉ cho phép frontend gọi API qua CORS:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
```

## 2. Chuẩn bị trước khi deploy

### 2.1. Kiểm tra các file quan trọng

Đảm bảo repo có các file sau:

- `render.yaml`
- `infra/docker/backend.Dockerfile`
- `backend/alembic.ini`
- `backend/alembic/versions/*`
- `frontend/package.json`

### 2.2. Commit và push code

```bash
git add .
git commit -m "Add free deployment setup"
git push origin main
```

Render và Vercel đều deploy từ GitHub, vì vậy code cần được push trước.

## 3. Deploy backend và database trên Render

### 3.1. Tạo Render Blueprint

1. Vào Render Dashboard.
2. Chọn **New** → **Blueprint**.
3. Connect GitHub repo này.
4. Render sẽ tự detect file `render.yaml`.
5. Chọn branch muốn deploy, thường là `main`.
6. Bấm tạo Blueprint.

Blueprint sẽ tạo:

- Web Service: `jobfit-ai-backend`
- PostgreSQL database: `jobfit-ai-db`

### 3.2. Backend environment variables

`render.yaml` đã khai báo phần lớn env vars. Sau khi có frontend URL từ Vercel, cần set thêm/sửa biến:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
```

Nếu muốn test tạm trước khi có Vercel URL, có thể để placeholder rồi sửa sau.

### 3.3. Database URLs

Render sẽ inject connection string cho:

```env
DATABASE_URL
SYNC_DATABASE_URL
```

Backend đã có logic tự normalize URL:

- `postgres://...` → `postgresql+asyncpg://...` cho runtime async
- `postgres://...` → `postgresql+psycopg://...` cho Alembic sync migrations

Vì vậy không cần tự sửa driver trong Render dashboard.

## 4. Chạy database migration

Sau khi Render tạo database xong, cần chạy migration một lần.

### Cách chạy trên Render Shell

1. Mở Render service `jobfit-ai-backend`.
2. Vào tab **Shell**.
3. Chạy:

```bash
alembic upgrade head
```

Migration đầu tiên có dòng:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Vì vậy database phải hỗ trợ extension `vector`/pgvector.

### Kiểm tra migration thành công

Nếu migration chạy thành công, command kết thúc không báo lỗi. Sau đó health check backend:

```text
https://your-backend.onrender.com/health
```

Kết quả mong đợi:

```json
{"status":"ok"}
```

## 5. Deploy frontend trên Vercel

### 5.1. Import repo

1. Vào Vercel Dashboard.
2. Chọn **Add New** → **Project**.
3. Import GitHub repo.
4. Ở phần project settings, set:

```text
Root Directory: frontend
Framework Preset: Next.js
Build Command: npm run build
Install Command: npm install
```

Thông thường Vercel tự detect Next.js, chỉ cần set đúng `Root Directory` là `frontend`.

### 5.2. Set frontend env var

Trong Vercel project settings, thêm:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

Thay `your-backend` bằng URL thật của Render backend.

### 5.3. Deploy

Bấm **Deploy**.

Sau khi deploy xong, Vercel sẽ cấp URL dạng:

```text
https://your-frontend.vercel.app
```

## 6. Cập nhật CORS backend

Sau khi có Vercel URL, quay lại Render backend và set:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
```

Sau đó redeploy hoặc restart backend service.

Nếu có nhiều frontend domain, phân tách bằng dấu phẩy:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app,https://your-custom-domain.com
```

## 7. Smoke test sau deploy

### 7.1. Test backend

Mở:

```text
https://your-backend.onrender.com/health
```

Kỳ vọng:

```json
{"status":"ok"}
```

### 7.2. Test frontend

Mở:

```text
https://your-frontend.vercel.app
```

Kiểm tra các route chính:

- `/`
- `/analyze`
- `/diagnostics`

### 7.3. Test luồng phân tích CV/JD

1. Mở `/analyze`.
2. Dùng demo data có sẵn hoặc paste CV/JD.
3. Submit analysis.
4. Kiểm tra report được tạo ở `/reports/{id}`.
5. Kiểm tra backend logs trên Render nếu có lỗi.

## 8. Troubleshooting

### Backend bị lỗi port trên Render

Đảm bảo `infra/docker/backend.Dockerfile` dùng dynamic port:

```dockerfile
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Không hardcode port `8000` khi deploy Render.

### Frontend gọi API bị CORS error

Kiểm tra Render env var:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
```

Không thêm dấu `/` cuối URL.

Sai:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app/
```

Đúng:

```env
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
```

### Migration lỗi `vector extension does not exist`

Database đang dùng không hỗ trợ pgvector. Cách xử lý:

1. Dùng provider PostgreSQL có hỗ trợ pgvector.
2. Hoặc bật extension `vector` nếu provider cho phép.
3. Sau đó chạy lại:

```bash
alembic upgrade head
```

### Vercel build lỗi vì gọi sai root directory

Đảm bảo Vercel project set:

```text
Root Directory: frontend
```

Nếu root directory để repo root, Vercel sẽ không thấy đúng `package.json` của frontend.

### Backend sleep trên Render Free

Render Free có thể sleep sau một thời gian không có traffic. Request đầu tiên sau khi sleep sẽ chậm hơn bình thường. Đây là giới hạn free tier.

### Upload file không bền vững

Backend đang lưu upload vào filesystem:

```env
UPLOAD_STORAGE_DIR=storage/uploads
```

Trên free hosting, filesystem có thể mất sau restart/redeploy. Với portfolio demo thì chấp nhận được. Nếu production, nên chuyển sang S3, Cloudflare R2 hoặc object storage tương tự.

## 9. Production checklist

Nếu muốn nâng cấp từ demo free lên production, nên làm thêm:

- Dùng paid backend service để tránh sleep.
- Dùng managed PostgreSQL có backup.
- Dùng object storage cho uploads.
- Set custom domain cho frontend và backend.
- Bật monitoring/log alert.
- Thêm rate limit cho API upload/analyze.
- Tách secret env vars khỏi repo.
- Chạy migration trong release step/CI thay vì chạy tay.

## 10. Env vars tham khảo

### Backend Render

```env
APP_ENV=production
LOG_LEVEL=INFO
DATABASE_URL=<render database url>
SYNC_DATABASE_URL=<render database url>
BACKEND_CORS_ORIGINS=https://your-frontend.vercel.app
AI_PROVIDER=local
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
UPLOAD_STORAGE_DIR=storage/uploads
MAX_UPLOAD_BYTES=10000000
URL_FETCH_TIMEOUT_SECONDS=10
MAX_URL_RESPONSE_BYTES=2000000
```

### Frontend Vercel

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.onrender.com
```

## 11. Deploy nhanh từng bước

Checklist ngắn:

1. Push code lên GitHub.
2. Render → New Blueprint → chọn repo → deploy `render.yaml`.
3. Render Shell → chạy `alembic upgrade head`.
4. Vercel → Import repo → Root Directory `frontend`.
5. Vercel env → set `NEXT_PUBLIC_API_BASE_URL`.
6. Deploy frontend.
7. Render env → set `BACKEND_CORS_ORIGINS` bằng Vercel URL.
8. Restart backend.
9. Test `/health` và `/analyze`.

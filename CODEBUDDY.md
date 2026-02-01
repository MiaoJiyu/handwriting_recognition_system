# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

This is a handwriting recognition system using Few-shot Learning to identify handwriting from assignments. The system consists of multiple microservices:

- **Backend API**: FastAPI-based REST API for authentication, user management, sample management, recognition requests, and training coordination. Located at `backend/`
- **Inference Service**: Standalone gRPC service for deep learning inference (Siamese Network + Few-shot Learning), image preprocessing, feature extraction, and model training. Located at `inference_service/`
- **Frontend**: React + TypeScript + Ant Design web interface at `frontend/`
- **Shared**: Common protobuf definitions and types at `shared/`

## Documentation

All project documentation is organized in the `docs/` directory.

### Quick Links

| Documentation | Description | Location |
|--------------|-------------|----------|
| **README** | Project introduction and quick start guide | [README](./README.md) |
| **Development Guide** | Detailed development setup and workflow | [DEVELOPMENT](./DEVELOPMENT.md) |
| **Implementation Check** | System architecture and feature verification | [IMPLEMENTATION_CHECK](./IMPLEMENTATION_CHECK.md) |
| **User Management Updates** | Batch operations and school management | [USER_MANAGEMENT_UPDATE](./USER_MANAGEMENT_UPDATE.md) |
| **PaddleOCR Fix** | OCR compatibility and fallback mechanism | [PADDLEOCR_FIX](./PADDLEOCR_FIX.md) |
| **Recognition Fix** | PCA training and recognition fixes | [RECOGNITION_FIX](./RECOGNITION_FIX.md) |
| **Paddle Version Fix** | PaddlePaddle version compatibility | [PADDLE_VERSION_FIX](./PADDLE_VERSION_FIX.md) |

## Common Development Commands

### Backend (FastAPI)

```bash
cd backend

# Setup environment (first time only)
cp .env.example .env
# Edit .env to configure database, JWT secret, etc.

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Run database migrations (REQUIRED before first run)
alembic upgrade head

# Start development server (recommended - handles Nix Python issues)
./run_server.sh

# Or start directly with uvicorn
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v
pytest --cov=app tests/

# Fix libstdc++ issues in Nix environments
./fix_venv.sh  # Recreates venv with system Python
```

**Backend Logs**: /tmp/backend.log

**Important**: If you encounter `libstdc++.so.6` or Nix Python-related errors, use `./fix_venv.sh` or `./run_server.sh`. These scripts automatically detect and use system Python instead of Nix Python to avoid library compatibility issues. The backend's `inference_client.py` also includes libstdc++ preloading logic for gRPC.

### Inference Service (gRPC + PyTorch)

```bash
cd inference_service

# Setup environment
cp .env.example .env
# Edit .env to configure database connection, model directory, etc.

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install PyTorch (choose CPU or GPU version)
# CPU version (faster for development/testing):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# GPU version (for production with NVIDIA GPU):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Regenerate protobuf files if .proto changes
./generate_proto.sh  # Or: python grpc_server/generate_proto.py

# Start gRPC server
python -m grpc_server.server

# Or use the startup script
./run_server.sh

# Run tests (CPU and GPU versions available)
pytest tests/ -v
pytest tests/test_deep_inference_cpu.py   # CPU-specific test
pytest tests/test_deep_inference_gpu.py   # GPU-specific test
```

**Note**: The inference service includes built-in libstdc++ preloading logic in `grpc_server/server.py` to handle Nix Python environments automatically.

### Frontend (React + TypeScript)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev -- --host 0.0.0.0

# Build for production
npm run build

# Preview production build
npm run preview

# Run tests
npm test                # Run all tests
npm run test:watch     # Run tests in watch mode
```
### Database Setup

```bash
# Create MySQL database
mysql -u root -p
CREATE DATABASE handwriting_recognition CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# Run migrations (from backend directory)
cd backend
alembic upgrade head

# Create new migration after modifying models
alembic revision --autogenerate -m "description"

# Review and edit the generated migration if needed
# vim alembic/versions/<migration_file>.py

# Apply migration
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Check current migration version
alembic current
```

### Docker Deployment

```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with production values (IMPORTANT: change SECRET_KEY and passwords)

# Start all services
docker-compose up -d

# View logs for specific services
docker-compose logs -f backend
docker-compose logs -f inference
docker-compose logs -f mysql

# Check service status
docker-compose ps

# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v

# Production deployment with Nginx
docker-compose --profile production up -d

# Rebuild specific service after code changes
docker-compose build backend
docker-compose up -d backend

# Access service logs
docker-compose logs -f --tail=100 backend
```

**Important**: Docker volumes are used for data persistence:
- `mysql_data`: MySQL database
- `redis_data`: Redis cache
- `uploads_data`: Uploaded samples and images
- `models_data`: Trained model files

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│                      Client Layer                             │
├─────────────────┬───────────────────┬───────────────────────┤
│   Web Frontend  │   Mobile (Future)  │                       │
│   (React)       │                   │                        │
└─────────────────┴───────────────────┴───────────────────────┘
         │
         │ HTTP/REST
         ▼
┌─────────────────┐  ┌─────────────────┬───────────────────────┤
│   Backend API   │  │  Inference Svc  │
│   (FastAPI)     │  │◄─┤  (gRPC + PyTorch)│
└─────────────────┘  └─────────────────┴───────────────────────┘
         │                    │
         ├────────────────────┤
         ▼                    ▼
    MySQL       │     Redis       │
(Primary DB)  │   (Cache)      │
```

### Backend API Structure

The backend is organized following a layered architecture:

- **`app/api/`**: FastAPI route handlers (auth, users, samples, recognition, training, schools, config)
- **`app/models/`**: SQLAlchemy ORM models (User, School, Sample, UserFeature, RecognitionLog, TrainingJob, Model)
- **`app/core/`**: Core configuration and database connection
- **`app/services/`**: Business logic layer (inference_client for gRPC communication)
- **`app/utils/`**: Utility functions (security, dependencies)
- **`alembic/`**: Database migration scripts

**Key Design Patterns**:
- FastAPI routers are organized by domain (auth, users, samples, etc.)
- Business logic is separated into services layer
- Pydantic models for request/response validation
- JWT-based authentication with role-based access control
- Async/await throughout for better performance

### Inference Service Structure

The inference service is organized by ML pipeline stages:

- **`preprocessing/`**: Image processing (image_processor, segmentation for print/handwriting separation, enhancement)
- **`feature_extraction/`**: Feature extraction (deep_features using PyTorch, traditional_features like LBP/Gabor, feature_fusion)
- **`matching/`**: Matching algorithms (similarity calculation, matcher)
- **`inference/`**: Main recognition orchestrator (recognizer.py)
- **`training/`**: Model training (trainer.py)
- **`model/`**: Neural network definitions (siamese_network.py)
- **`grpc_server/`**: gRPC service implementation (server.py, protobuf definitions)
- **`core/`**: Configuration

**Key Design Patterns**:
- Pipeline architecture: preprocessing → feature extraction → matching
- Deep learning (Siamese Network) + traditional features (LBP, Gabor) hybrid approach
- Feature fusion combines both approaches for better accuracy
- Async gRPC service for high-performance inference
- Training runs asynchronously to avoid blocking recognition requests

### Communication Between Services

**Backend → Inference Service**: gRPC protocol
- Backend uses `app/services/inference_client.py` to communicate with inference service
- The client reuses protobuf generated code from `inference_service/grpc_server/` by adding repo root to sys.path
- Protobuf definitions in `shared/proto/handwriting_inference.proto`
- Inference service listens on port 50051 by default
- Available gRPC methods:
  - `Recognize()`: Single image recognition
  - `BatchRecognize()`: Batch image recognition
  - `TrainModel()`: Trigger model training (async)
  - `GetTrainingStatus()`: Query training progress
  - `UpdateConfig()`: Update recognition parameters (thresholds, top_k)

**Frontend → Backend**: HTTP/REST API
- All frontend API calls go through backend API at port 8000
- JWT token stored in localStorage for authentication
- Axios for HTTP requests with React Query for data fetching
- API endpoints documented at `http://localhost:8000/docs` (Swagger UI)

### Database Schema

Key tables:
- **users**: User accounts with roles (system_admin, school_admin, teacher, student)
- **schools**: School/organization hierarchy
- **samples**: Uploaded handwriting samples with crop regions
- **user_features**: Pre-computed feature vectors for each user (cached from inference service)
- **recognition_logs**: Recognition request history
- **training_jobs**: Training task tracking
- **models**: Model version management

### Frontend Architecture

- **`src/pages/`**: Page components (Login, Dashboard, SampleList, SampleUpload, Recognition, etc.)
- **`src/components/`**: Reusable components (Layout, ImageCropper)
- **`src/services/`**: API client functions
- **`src/contexts/`**: React Context for global state (Auth context)
- **`src/types/`**: TypeScript type definitions

**Key Technologies**:
- React Router for navigation
- Ant Design for UI components
- React Query for server state management
- Axios for HTTP requests

## Important Configuration

### Backend Configuration (`backend/.env`)

Critical settings that must be configured:

```bash
# Database - REQUIRED
DATABASE_URL=mysql+pymysql://user:password@host:3306/handwriting_recognition?charset=utf8mb4

# JWT Secret - CHANGE IN PRODUCTION!
SECRET_KEY=your-super-secret-key-at-least-32-characters

# Inference service connection
INFERENCE_SERVICE_HOST=localhost
INFERENCE_SERVICE_PORT=50051

# CORS origins - add frontend URLs
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# File storage
UPLOAD_DIR=./uploads
SAMPLES_DIR=./uploads/samples
MODELS_DIR=./models

# 文件上传配置
MAX_UPLOAD_SIZE=10485760  # 单位：字节，默认10MB (10 * 1024 * 1024 = 10485760)
```

### Inference Service Configuration (`inference_service/.env`)

```bash
# gRPC server
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# Recognition parameters
SIMILARITY_THRESHOLD=0.7  # 最小相似度分数
GAP_THRESHOLD=0.1          # Top-1和Top-2之间最小分数差距
TOP_K=5                    # 返回结果数量

# Database (for user_features cache)
DATABASE_URL=mysql+pymysql://user:password@host:3306/handwriting_recognition?charset=utf8mb4
```

### Frontend Configuration (`frontend/vite.config.ts`)

The API proxy target must match backend URL:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  }
}
```

## Development Workflow

### Adding a New API Endpoint

1. Define Pydantic models in `backend/app/api/` if needed
2. Implement route handler in appropriate `app/api/*.py` file
3. Add business logic in `app/services/` if complex
4. Test using Swagger UI at `http://localhost:8000/docs`
5. Add corresponding frontend service in `frontend/src/services/`

### Database Schema Changes

1. Modify or create SQLAlchemy model in `backend/app/models/`
2. Generate migration: `alembic revision --autogenerate -m "description"`
3. Review and edit the generated migration in `backend/alembic/versions/`
4. Apply migration: `alembic upgrade head`

### Adding New Features to Inference Service

1. Implement logic in appropriate module (preprocessing, feature_extraction, matching, inference, training)
2. If adding new gRPC method:
   - Update protobuf definition in `shared/proto/handwriting_inference.proto`
   - Regenerate protobuf files: `cd inference_service && ./generate_proto.sh`
   - Implement new method in `inference_service/grpc_server/server.py`
3. Update inference client in `backend/app/services/inference_client.py` to call new gRPC method
4. The client automatically adds repo root to sys.path to import protobuf files from inference_service

## Troubleshooting

### libstdc++ Issues in Nix Environments

If you see errors about `libstdc++.so.6` or `version GLIBCXX_3.4.x not found`, or other library issues:

```bash
cd backend
./fix_venv.sh  # Recreates venv with system Python
```

**Root cause**: Nix-managed Python environments have different library paths than system libraries. Both backend and inference service include libstdc++ preloading code to work around this.

**Locations of fix code**:
- `backend/run_server.sh`: Detects system Python and sets LD_LIBRARY_PATH
- `backend/fix_venv.sh`: Recreates venv with system Python
- `backend/app/services/inference_client.py`: Preloads libstdc++ for gRPC
- `inference_service/grpc_server/server.py`: Preloads libstdc++ for gRPC

### Database Connection Issues

Check:
1. MySQL service is running:
   - Local: `systemctl status mysql`
   - Docker: `docker-compose ps mysql`
2. Database exists: `mysql -u root -p -e "SHOW DATABASES;"`
3. `.env` file has correct DATABASE_URL format
4. User permissions: Ensure MySQL user has SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER privileges
5. Alembic migrations applied: `cd backend && alembic current`

### Inference Service Connection Timeout

Check:
1. Inference service is running:
   ```bash
   ps aux | grep python | grep grpc_server
   # Or check Docker: docker-compose ps inference
   ```
2. Port is accessible: `netstat -tlnp | grep 50051` (or `ss -tlnp | grep 50051`)
3. Backend `.env` has correct INFERENCE_SERVICE_HOST/PORT
4. No firewall blocking port 50051: `sudo ufw status` or `sudo iptables -L`
5. Test gRPC connection manually:
   ```bash
   python -c "import grpc; ch = grpc.insecure_channel('localhost:50051'); print('OK')"
   ```

### Frontend CORS Errors

Check:
1. Backend `CORS_ORIGINS` in `.env` includes frontend URL:
   ```bash
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173
   ```
2. Frontend `VITE_API_URL` in `vite.config.ts` or `.env` matches backend address
3. JWT token is valid and included in Authorization header: `Bearer <token>`
4. Backend has custom CORS middleware for `/uploads/*` static files (see `backend/app/main.py:32-53`)

### User Management Page Issues

**"确定" button not working**:
- Check that form has `onFinish` prop defined in UserManagement.tsx
- Verify form instance is properly created with `Form.useForm()`

**System configuration not displaying**:
- Ensure backend API returns all required fields (database_url, inference_service, redis, upload_dir, samples_dir, models_dir, max_upload_size, cors_origins)
- Check that SystemManagement.tsx uses multiple `Descriptions` components instead of `items` prop

**User creation time not showing**:
- Verify `UserResponse` model includes `created_at` field with proper datetime serialization
- Use `@field_serializer` decorator to convert datetime to ISO format string

### Recognition Returns No Results or "Unknown" User

Check:
1. Training has been completed and status is "completed"
2. User features exist in `user_features` table:
   ```sql
   SELECT COUNT(*) FROM user_features;
   ```
3. Similarity threshold (`SIMILARITY_THRESHOLD`) is not too high (default 0.7)
4. Image preprocessing is working correctly (check inference service logs)
5. Model file exists in `inference_service/models/` or ImageNet fallback is working

### Training/Inference Issues

**PCA dimension mismatch error**:
- Error: `Found array with dim X, while dim <= Y is required by PCA.`
- Cause: Feature array has wrong dimension (3D instead of 2D)
- Solution: Use `np.squeeze(features_array, axis=1)` to remove extra dimension
- Location: `inference_service/training/trainer.py:347`

**All users showing same similarity score (e.g., all 52.15%)**:
- This indicates features are not being properly extracted or PCA is not differentiating users
- Check user_features table contains unique feature vectors for each user
- Verify training used sufficient samples per user (at least 2-3 samples recommended)
- Check inference service logs for feature extraction errors
- Review similarity calculation in `inference_service/matching/matcher.py`

## Key File Locations

### Backend
- `backend/app/main.py`: FastAPI application entry point, CORS middleware, static file serving
- `backend/app/core/config.py`: Configuration management
- `backend/app/api/`: REST API route handlers
- `backend/app/services/inference_client.py`: gRPC client for communicating with inference service
- `backend/app/models/`: SQLAlchemy ORM models
- `backend/alembic/versions/`: Database migration scripts
- `backend/requirements.txt`: Python dependencies (includes PaddlePaddle, PaddleOCR, OpenPyXL)

### Inference Service
- `inference_service/grpc_server/server.py`: gRPC server implementation with 5 methods
- `inference_service/inference/recognizer.py`: Main recognition orchestrator
- `inference_service/training/trainer.py`: Model training orchestrator
- `inference_service/matching/matcher.py`: Similarity matching logic
- `inference_service/preprocessing/`: Image processing modules
- `inference_service/feature_extraction/`: Feature extraction modules
- `inference_service/model/siamese_network.py`: Siamese Network definition
- `inference_service/core/config.py`: Configuration

### Shared
- `shared/proto/handwriting_inference.proto`: gRPC service definition
- `shared/types.py`: Shared type definitions
- `shared/constants.py`: Shared constants

### Frontend
- `frontend/src/pages/`: Page components (Login, Dashboard, SampleList, SampleUpload, Recognition, UserManagement, SystemManagement)
- `frontend/src/components/`: Reusable components (Layout, ImageCropper)
- `frontend/src/services/`: API client functions (api.ts, config.ts)
- `frontend/src/contexts/`: React Context (Auth context)
- `frontend/src/types/`: TypeScript type definitions
- `frontend/vite.config.ts`: Vite configuration including API proxy
- `frontend/package.json`: Dependencies (includes xlsx)

### Documentation
- `docs/README.md`: Project introduction and quick start
- `docs/DEVELOPMENT.md`: Detailed development setup and workflow
- `docs/IMPLEMENTATION_CHECK.md`: System architecture and feature verification
- `docs/USER_MANAGEMENT_UPDATE.md`: User management batch operations and school management
- `docs/PADDLEOCR_FIX.md`: OCR compatibility and fallback mechanism
- `docs/RECOGNITION_FIX.md`: PCA training and recognition fixes
- `docs/PADDLE_VERSION_FIX.md`: PaddlePaddle version compatibility fix

## Recent Updates

### Frontend Bug Fixes (2026-01-30)
- ✅ Fixed UserManagement page: Added missing `form` instance for single user creation
- ✅ Fixed SystemManagement page: Added missing `useQueryClient` import
- ✅ Fixed user creation time: Added `created_at` field to `UserResponse` with datetime serialization
- ✅ Fixed system configuration display: Restructured `Descriptions` components and added missing fields
- ✅ Fixed operation history: Added Timeline component to display recent system operations
- ✅ Fixed user list query: Corrected datetime type mismatch in API response

### Recognition System Fixes (NEW)
- ✅ Fixed PCA training to use all samples and save model
- ✅ Fixed PCA dimension mismatch between training and recognition
- ✅ Implemented PCA model persistence (models/pca.pkl)
- ✅ Added OpenCV fallback mechanism for PaddleOCR failures
- ✅ Updated PaddlePaddle version to compatible 2.6.2
- ✅ Fixed feature array dimension issue in trainer.py (3D → 2D)
- ✅ Added PCA save functionality in `fit_pca()` method

### Upload Size Configuration (NEW)
- ✅ Configurable max upload size via .env
- ✅ Backend validation with HTTP 413 error
- ✅ Frontend validation with configurable limits
- ✅ 10MB default limit

### System Management Features (NEW)
- ✅ System reload API endpoint for admins
- ✅ System configuration endpoint
- ✅ Frontend system management page with configuration display
- ✅ Operation history timeline for tracking system changes
- ✅ Hot-reload capability without service restart

### User Management Features (NEW)
- ✅ Batch student creation with automatic ID and password generation
- ✅ Excel import/export for student management
- ✅ School selection and filtering for multi-school deployments
- ✅ Teacher role can manage students
- ✅ System administrator role can manage all schools

### Upload Size Configuration (NEW)
- ✅ Configurable max upload size via .env
- ✅ Backend validation with HTTP 413 error
- ✅ Frontend validation with configurable limits
- ✅ 10MB default limit

## Model and Feature Management

### Feature Extraction Pipeline
- Deep Learning: PyTorch Siamese Network (256-dim features)
- Traditional Features: LBP + Gabor filters
- Feature Fusion: Combines both approaches
- PCA Dimensionality Reduction: For efficiency
- Normalization: L2 normalization on features

### Training Workflow
1. Samples uploaded via frontend
2. Teacher triggers training via `POST /api/training/start`
3. Backend creates training job record
4. Inference service trains Siamese Network asynchronously
5. Features extracted and saved to `user_features` table
6. PCA model trained and persisted to disk
7. Training job status updated to "completed"

### Recognition Workflow
1. Image uploaded via frontend `POST /api/recognition`
2. Backend saves to temporary file
3. Inference service extracts features (deep + traditional)
4. Features normalized and PCA transformed
5. Loaded user features from database
6. Cosine similarity calculated
7. Top-k results with confidence scores
8. Results returned to frontend

## Testing Strategy

### Backend
- pytest for API endpoint testing (currently minimal - smoke test only)
- Inference service has CPU/GPU inference tests
- Manual testing via Swagger UI at `http://localhost:8000/docs`

### Frontend
- vitest for component testing
- Manual testing of user flows

### Integration Testing
1. Test complete flow: User registration → Sample upload → Training → Recognition
2. Test all roles: system_admin, school_admin, teacher, student
3. Test file upload size limits
4. Test system reload functionality

## Common Issues and Solutions

See individual documentation files for detailed troubleshooting of specific issues.

## Code Structure Overview

### Backend API Organization

```
backend/app/
├── api/
│   ├── auth.py              # Authentication endpoints (login, register)
│   ├── users.py            # User management (CRUD + batch operations)
│   ├── samples.py          # Sample upload, list, delete
│   ├── recognition.py       # Recognition endpoint
│   ├── training.py          # Training coordination
│   ├── schools.py          # School management
│   ├── config.py           # System configuration endpoint
│   ├── system.py           # System management endpoint
│   └── token.py            # Token API for external integration
├── models/
│   ├── user.py              # User ORM model
│   ├── school.py            # School ORM model
│   ├── sample.py            # Sample ORM model
│   ├── user_feature.py       # User feature ORM model
│   ├── recognition_log.py    # Recognition log ORM model
│   ├── training_job.py       # Training job ORM model
│   └── model.py             # Model ORM model
├── core/
│   ├── config.py             # Settings management
│   └── database.py          # Database connection
├── services/
│   └── inference_client.py  # gRPC communication
└── utils/
    ├── dependencies.py        # Auth dependencies
    └── security.py            # Password hashing
```

### Inference Service Organization

```
inference_service/
├── grpc_server/
│   ├── server.py            # gRPC server with 5 methods
│   └── generate_proto.py  # Protobuf generation
├── inference/
│   ├── recognizer.py         # Main recognition orchestrator
│   ├── training/
│   │   └── trainer.py      # Model training
│   ├── matching/
│   │   └── matcher.py         # Similarity calculation
│   ├── preprocessing/
│   │   ├── image_processor.py
│   │   └── segmentation.py
│   ├── feature_extraction/
│   │   ├── deep_features.py   # PyTorch features
│   │   ├── traditional_features.py
│   │   └── feature_fusion.py
│   └── model/
│       └── siamese_network.py
└── core/
    └── config.py             # Configuration
```

### Frontend Organization

```
frontend/src/
├── pages/
│   ├── Login.tsx
│   ├── Dashboard.tsx
│   ├── SampleList.tsx
│   ├── SampleUpload.tsx
│   ├── Recognition.tsx
│   ├── UserManagement.tsx  # Updated with batch operations
│   └── SystemManagement.tsx
├── components/
│   ├── Layout.tsx           # App layout with navigation
│   └── ImageCropper.tsx     # Image cropping component
├── services/
│   ├── api.ts               # Main API client
│   ├── config.ts            # Configuration API client
│   └── auth.ts              # Auth service client
├── contexts/
│   └── AuthContext.tsx        # Authentication context
└── types/
    └── index.ts              # TypeScript type definitions
```

## Getting Started

### Prerequisites
1. Python 3.8 or higher
2. Node.js 16 or higher
3. MySQL 8.0 or higher
4. (Optional) Docker and Docker Compose

### First Time Setup

1. Clone repository
2. Configure backend environment:
   ```bash
   cd backend
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. Start services:
   ```bash
   # Start MySQL (or use Docker)
   docker-compose up -d mysql redis

   # Start backend
   cd backend
   ./run_server.sh

   # Start inference service
   cd inference_service
   python -m grpc_server.server
   ```

4. Install frontend dependencies and start:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. Access application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Project Information

This is a handwriting recognition system using Few-shot Learning to identify handwriting from assignments. For more information, see the documentation in the `docs/` directory.

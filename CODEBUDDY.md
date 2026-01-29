# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

This is a handwriting recognition system using Few-shot Learning to identify handwriting from assignments. The system consists of multiple microservices:

- **Backend API**: FastAPI-based REST API for authentication, user management, sample management, recognition requests, and training coordination. Located at `backend/`
- **Inference Service**: Standalone gRPC service for deep learning inference (Siamese Network + Few-shot Learning), image preprocessing, feature extraction, and model training. Located at `inference_service/`
- **Frontend**: React + TypeScript + Ant Design web interface at `frontend/`
- **Desktop**: PyQt6 desktop application at `desktop/`
- **Shared**: Common protobuf definitions and types at `shared/`

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
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest tests/ -v
pytest --cov=app tests/

# Fix libstdc++ issues in Nix environments
./fix_venv.sh  # Recreates venv with system Python
```

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
pytest tests/test_deep_inference_cpu.py  # CPU-specific test
pytest tests/test_deep_inference_gpu.py  # GPU-specific test
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
npm test

# Run tests in watch mode
npm run test:watch
```

### Desktop (PyQt6)

```bash
cd desktop

# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run desktop application
python main.py
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

### Testing

```bash
# Backend tests
cd backend
pytest tests/ -v                    # Run all tests with verbose output
pytest --cov=app tests/             # Run with coverage report
pytest tests/test_smoke.py          # Run specific test file
pytest -k "test_name"              # Run tests matching pattern

# Inference service tests
cd inference_service
pytest tests/ -v
pytest tests/test_deep_inference_cpu.py   # CPU inference test
pytest tests/test_deep_inference_gpu.py   # GPU inference test (requires GPU)

# Frontend tests
cd frontend
npm test                # Run all tests
npm run test:watch     # Run tests in watch mode
```

**Note**: Test coverage is currently minimal. The backend has a smoke test, and inference service has CPU/GPU inference tests.

## Architecture Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                             │
├─────────────────┬───────────────────┬───────────────────────┤
│   Web Frontend  │   Desktop (PyQt6)  │   Mobile (Future)      │
│   (React)       │                   │                        │
└────────┬────────┴─────────┬─────────┴───────────────────────┘
         │                  │
         │ HTTP/REST        │ gRPC
         ▼                  ▼
┌─────────────────┐  ┌─────────────────┐
│   Backend API   │  │  Inference Svc  │
│   (FastAPI)     │◄─┤  (gRPC + PyTorch)│
└────────┬────────┘  └────────┬────────┘
         │                    │
         ├────────────────────┤
         ▼                    ▼
┌─────────────────┐  ┌─────────────────┐
│     MySQL       │  │     Redis       │
│   (Primary DB)  │  │    (Cache)      │
└─────────────────┘  └─────────────────┘
```

### Backend API Structure

The backend is organized following a layered architecture:

- **`app/api/`**: FastAPI route handlers (auth, users, samples, recognition, training, schools)
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
```

### Inference Service Configuration (`inference_service/.env`)

```bash
# gRPC server
GRPC_HOST=0.0.0.0
GRPC_PORT=50051

# Recognition parameters
SIMILARITY_THRESHOLD=0.7  # Minimum similarity score
GAP_THRESHOLD=0.1          # Gap between top scores
TOP_K=5                    # Number of results to return

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
3. Review generated migration in `backend/alembic/versions/`
4. Apply migration: `alembic upgrade head`

### Adding New Features to Inference Service

1. Implement logic in appropriate module (preprocessing, feature_extraction, matching, inference)
2. If adding new gRPC method:
   - Update protobuf definition in `shared/proto/handwriting_inference.proto`
   - Regenerate protobuf files: `cd inference_service && ./generate_proto.sh`
   - Implement new method in `inference_service/grpc_server/server.py`
3. Update inference client in `backend/app/services/inference_client.py` to call new gRPC method
4. The client automatically adds repo root to sys.path to import protobuf files from inference_service

**Key Classes**:
- `inference/inference/recognizer.py`: Main recognition orchestrator
  - Loads user features from `user_features` table
  - Orchestrates: preprocessing → feature extraction → matching
  - Uses Redis for caching (optional)
- `inference/training/trainer.py`: Model training orchestrator
  - Trains Siamese Network asynchronously
  - Updates training job status in database
- `inference/matching/matcher.py`: Similarity matching logic
  - Implements gap threshold and similarity threshold logic
  - Returns top-k results with confidence scores

## Common Issues and Solutions

### libstdc++ Issues in Nix Environments

If you see errors about `libstdc++.so.6`, `version GLIBCXX_3.4.x not found`, or other library issues:

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
3. `.env` file has correct DATABASE_URL format:
   ```bash
   mysql+pymysql://user:password@host:3306/handwriting_recognition?charset=utf8mb4
   ```
4. Alembic migrations applied: `cd backend && alembic current`
5. User permissions: Ensure MySQL user has SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER privileges

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
   CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://your-frontend.com
   ```
2. Frontend `VITE_API_URL` in `vite.config.ts` or `.env` matches backend address
3. JWT token is valid and included in Authorization header: `Bearer <token>`
4. Backend has custom CORS middleware for `/uploads/*` static files (see `backend/app/main.py:32-53`)

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

## Model and Feature Management

### Model Storage
- **Model files**: Stored in `inference_service/models/` directory
- In Docker, this is mounted as a volume (`models_data`) for persistence
- If no `.pth` file exists, the system uses ImageNet pre-trained weights as fallback
- Model version tracking in `models` table

### Feature Cache
- **User features**: Pre-computed feature vectors stored in `user_features` table
- Features are extracted during training and cached for faster recognition
- The inference service loads these features from the database for each recognition request
- Feature format: JSON-serialized numpy arrays

### Training Workflow
1. Samples are uploaded via frontend (`POST /api/samples/upload`)
2. Teacher triggers training via frontend (`POST /api/training/start`)
3. Backend creates a `training_job` record and calls gRPC `TrainModel()`
4. Inference service trains asynchronously:
   - Loads all user samples from database
   - Trains Siamese Network
   - Extracts features for each user
   - Saves features to `user_features` table
   - Updates `training_job` status to "completed"
5. New models and features are available immediately for recognition

### Feature Extraction Pipeline
- **Deep Learning**: PyTorch Siamese Network (256-dim features)
- **Traditional Features**: LBP (Local Binary Patterns) + Gabor filters
- **Fusion**: Both feature types are combined using weighted fusion
- Final feature vector is stored in database for matching

## Testing Strategy

- **Backend**: pytest for API endpoint testing (currently minimal - smoke test only)
- **Inference Service**: pytest for model inference testing (both CPU and GPU versions available)
- **Frontend**: vitest for component testing
- **Manual Testing**: Swagger UI at `http://localhost:8000/docs` for API exploration

## Recognition Flow

When a user uploads an image for recognition:

1. **Frontend**: User uploads image via `POST /api/recognition` (multipart/form-data)
2. **Backend API** (`app/api/recognition.py`):
   - Validates request and user authentication
   - Saves uploaded image to `uploads/` directory
   - Calls gRPC `Recognize()` method via `inference_client.py`
3. **Inference Service** (`inference/inference/recognizer.py`):
   - Preprocesses image: `ImageProcessor.process_sample()` (print/handwriting separation, enhancement)
   - Extracts features: `FeatureFusion.extract_fused_features()` (deep + traditional features)
   - Loads user features from `user_features` table
   - Matches against feature library: `Matcher.match()` (similarity calculation, gap threshold)
   - Returns top-k results with confidence scores
4. **Backend API**: Returns results to frontend in JSON format
5. **Frontend**: Displays recognition results with confidence scores

**Key Parameters**:
- `SIMILARITY_THRESHOLD` (default 0.7): Minimum similarity score to consider a match
- `GAP_THRESHOLD` (default 0.1): Minimum gap between top-1 and top-2 scores to prevent false matches
- `TOP_K` (default 5): Number of results to return

## Important File Locations

### Backend
- `backend/app/main.py`: FastAPI application entry point, CORS middleware, static file serving
- `backend/app/core/config.py`: Configuration management using Pydantic Settings
- `backend/app/services/inference_client.py`: gRPC client for communicating with inference service
- `backend/app/api/`: REST API route handlers (auth, users, samples, recognition, training, schools)
- `backend/app/models/`: SQLAlchemy ORM models
- `backend/alembic/versions/`: Database migration scripts

### Inference Service
- `inference_service/grpc_server/server.py`: gRPC server implementation with 5 methods
- `inference_service/inference/recognizer.py`: Main recognition orchestrator
- `inference_service/training/trainer.py`: Model training orchestrator
- `inference_service/preprocessing/`: Image processing modules (segmentation, enhancement)
- `inference_service/feature_extraction/`: Feature extraction modules (deep, traditional, fusion)
- `inference_service/matching/`: Similarity matching algorithms
- `inference_service/model/siamese_network.py`: Siamese Network definition
- `inference_service/models/`: Model weights directory

### Shared
- `shared/proto/handwriting_inference.proto`: gRPC service definition
- `shared/types.py`: Shared type definitions
- `shared/constants.py`: Shared constants

### Frontend
- `frontend/src/pages/`: Page components (Login, Dashboard, SampleList, Recognition, etc.)
- `frontend/src/components/`: Reusable components (Layout, ImageCropper)
- `frontend/src/services/`: API client functions
- `frontend/src/contexts/`: React Context for global state
- `frontend/src/types/`: TypeScript type definitions
- `frontend/vite.config.ts`: Vite configuration including API proxy

## Development Tips

### Starting All Services Locally

For full local development:

```bash
# Terminal 1: Start MySQL and Redis (if not using Docker)
# Or use: docker-compose up -d mysql redis

# Terminal 2: Start backend
cd backend
source venv/bin/activate
./run_server.sh  # or: uvicorn app.main:app --reload

# Terminal 3: Start inference service
cd inference_service
source venv/bin/activate
python -m grpc_server.server  # or: ./run_server.sh

# Terminal 4: Start frontend
cd frontend
npm run dev
```

Access:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Inference Service: localhost:50051 (gRPC)

### Debugging

- **Backend**: Use VS Code debugger or add `import pdb; pdb.set_trace()` breakpoints
- **Inference Service**: Add logging in `inference_service/inference/recognizer.py` or other modules
- **gRPC Communication**: Check logs in both `backend/app/services/inference_client.py` and `inference_service/grpc_server/server.py`
- **Database**: Use MySQL CLI or tools like DBeaver, TablePlus to inspect `user_features`, `samples`, `training_jobs` tables

### Performance Optimization

- Inference service loads user features from database on each recognition request. For high-load scenarios, consider Redis caching.
- Feature extraction is the bottleneck. GPU acceleration significantly improves performance.
- Model training is asynchronous and doesn't block recognition requests.
- Use batch recognition (`BatchRecognize`) for processing multiple images efficiently.

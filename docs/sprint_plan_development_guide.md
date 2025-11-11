# LepSoc Validation System - Sprint Plan & Development Guide

## 📦 Deliverables Created

You now have 5 comprehensive files ready for development:

1. **`lepsoc_validation_app_specification.md`** - Complete 12-section specification document
2. **`lepsoc_crewai_validator.py`** - Full CrewAI implementation with all 16 agents
3. **`lovable_frontend_instructions.md`** - Detailed Lovable.dev frontend specs
4. **`requirements.txt`** - All Python dependencies
5. **`README.md`** - Project documentation

## 🚀 How to Use These Files in Claude Code

### Step 1: Project Setup in Claude Code
```bash
# Create project structure
mkdir lepsoc-validator
cd lepsoc-validator
mkdir -p backend frontend data/{input,output} tests docs

# Copy the Python validator
cp lepsoc_crewai_validator.py backend/validator.py

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Required Services
```bash
# Start Ollama (for local LLM)
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull llama2

# Start iNaturalist MCP Server  
docker run -d -p 8811:8811 --name inat-mcp coloradeo/inat-mcp:latest
```

### Step 3: Test Basic Validation
```bash
# Test with sample data
python backend/validator.py data/input/test.xlsx data/output/validated.xlsx
```

## 📋 5-Week Sprint Plan

### SPRINT 1: Foundation & Basic Agents (Current Week)
**Goal:** Get core infrastructure working

#### Day 1-2: Environment Setup ✅
- [x] Install Python, Docker, Node.js
- [x] Set up Ollama with llama2 model
- [x] Configure iNaturalist MCP server
- [x] Create project structure

#### Day 3-4: Basic Validation Pipeline
```python
# In Claude Code, focus on:
1. Test the existing validator.py with sample data
2. Verify all 16 agents initialize correctly
3. Create test Excel file with 10 rows
4. Run validation and check output
```

#### Day 5: API Foundation
```python
# Create backend/api.py
from fastapi import FastAPI, UploadFile
from validator import LepSocValidationCrew

app = FastAPI()

@app.post("/api/validate/upload")
async def upload_file(file: UploadFile):
    # Save file and start validation
    pass
```

**Deliverables:**
- Working validator with 16 agents
- Basic API with upload endpoint
- Test results from sample data

---

### SPRINT 2: iNaturalist Integration (Week 2)
**Goal:** Connect species/location validation to iNaturalist

#### Day 1-2: Species Validation
```python
# Enhance FamilyValidator, GenusValidator, SpeciesValidator
# Add actual iNat API calls using the INatValidator class
async def validate_with_inat(genus, species):
    validator = INatValidator()
    result = await validator.check_species(genus, species)
    return result
```

#### Day 3: Location Validation
```python
# Enhance CountyValidator
# Add place validation via iNat
async def validate_location(county, state):
    validator = INatValidator()
    result = await validator.check_location(county, state, "USA")
    return result
```

#### Day 4-5: Record Detection
```python
# Implement state/county record checking
async def check_if_new_record(taxon_id, state, county):
    validator = INatValidator()
    result = await validator.check_record_status(taxon_id, state=state, county=county)
    return result['is_new_record']
```

**Deliverables:**
- Full iNat integration working
- Record detection functional
- API endpoints for status checking

---

### SPRINT 3: Frontend Development (Week 3)
**Goal:** Build Lovable frontend

#### Day 1: Lovable Setup
1. Go to Lovable.dev
2. Create new project
3. Copy `lovable_frontend_instructions.md` content
4. Generate initial components

#### Day 2-3: Core Components
- FileUpload component
- ValidationProgress component
- ReviewTable component

#### Day 4-5: Integration
```javascript
// Connect to backend API
const API_BASE = 'http://localhost:8000';

async function startValidation(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE}/api/validate/upload`, {
        method: 'POST',
        body: formData
    });
    return response.json();
}
```

**Deliverables:**
- Complete frontend in Lovable
- API integration working
- File upload → validation → download flow

---

### SPRINT 4: Human Review & Polish (Week 4)
**Goal:** Implement review workflow

#### Day 1-2: Review Interface
```python
# Add review endpoints
@app.get("/api/validate/review/{validation_id}")
async def get_review_items(validation_id: str):
    # Return flagged items
    pass

@app.post("/api/validate/approve/{validation_id}")
async def approve_corrections(validation_id: str, corrections: dict):
    # Apply human corrections
    pass
```

#### Day 3: Metadata Tracking
```python
# Enhanced metadata structure
metadata = {
    "changes": [],
    "new_state_records": [],
    "new_county_records": [],
    "human_reviews": [],
    "confidence_scores": {}
}
```

#### Day 4-5: Testing & Optimization
- Load test with 1000+ row files
- Optimize validation speed
- Add caching for iNat calls

**Deliverables:**
- Human review workflow complete
- Metadata tracking operational
- Performance optimized

---

### SPRINT 5: Production Ready (Week 5)
**Goal:** Deploy and document

#### Day 1-2: Testing
```bash
# Run comprehensive tests
pytest tests/ -v --cov=backend
```

#### Day 3: Docker Deployment
```dockerfile
# Create Dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Day 4: Documentation
- API documentation
- User guide
- Deployment guide

#### Day 5: Launch
- Deploy to production
- Final testing
- Handover

**Deliverables:**
- Docker containers
- Complete documentation
- Production deployment

---

## 💻 Development Commands for Claude Code

### Quick Commands to Copy/Paste

```bash
# 1. Initial Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Start Services
docker-compose up -d

# 3. Run Validator
python backend/validator.py test.xlsx output.xlsx

# 4. Start API Server
uvicorn backend.api:app --reload --port 8000

# 5. Run Tests
pytest tests/ -v

# 6. Format Code
black backend/ --line-length 100
isort backend/

# 7. Type Checking
mypy backend/

# 8. Generate Docs
sphinx-build -b html docs/source docs/build

# 9. Build Docker Image
docker build -t lepsoc-validator .

# 10. Run Production
docker run -p 8000:8000 lepsoc-validator
```

---

## 🎯 Success Metrics

Track these KPIs during development:

1. **Validation Accuracy**: Target 99% for species names
2. **Processing Speed**: < 5 minutes for 1000 rows
3. **False Positives**: < 0.1% for record detection
4. **User Experience**: < 5 clicks to complete review
5. **Test Coverage**: > 80% code coverage

---

## 🔧 Troubleshooting in Claude Code

### Common Issues & Solutions

**Issue: Ollama not responding**
```bash
# Restart Ollama
docker restart ollama
docker exec -it ollama ollama pull llama2
```

**Issue: iNat API timeout**
```python
# Increase timeout in INatValidator
self.timeout = 30  # seconds
```

**Issue: Memory issues with large files**
```python
# Process in chunks
chunk_size = 100
for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i+chunk_size]
    process_chunk(chunk)
```

**Issue: CrewAI agents not working**
```python
# Check Ollama connection
import requests
response = requests.get('http://localhost:11434/api/tags')
print(response.json())  # Should show llama2
```

---

## 📝 Next Steps in Claude Code

1. **Copy all provided files** to your project
2. **Set up environment** with requirements.txt
3. **Start Docker services** (Ollama, iNat MCP)
4. **Test the validator** with sample data
5. **Build API endpoints** using FastAPI
6. **Create frontend** in Lovable using instructions
7. **Iterate through sprints** week by week

---

## 🎉 Ready to Start!

You now have everything needed to build the LepSoc Validation System:
- ✅ Complete specification
- ✅ Working CrewAI code
- ✅ Frontend instructions
- ✅ Sprint plan
- ✅ All dependencies

Start with Sprint 1, Day 1 and work through the plan. The simple CrewAI implementation is ready to run - just add your data and watch the agents validate!

**Remember:** Keep it SIMPLE! The code provided is intentionally straightforward. Focus on getting it working first, then optimize.

Good luck with your development! 🦋

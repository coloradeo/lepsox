# LepSoc Season Summary Validation System
## Application Specification Document
**Version:** 1.0  
**Date:** November 2024  

---

## 1. EXECUTIVE SUMMARY

The LepSoc Season Summary Validation System is a data validation application designed to process annual Lepidopterist Society observation submissions. The system employs a CrewAI agent-based architecture with one specialized agent per data column, integrating with iNaturalist APIs for species and location validation, and includes human-in-the-loop review capabilities.

### Key Features:
- Row-by-row Excel/CSV data validation
- Automated species and location verification via iNaturalist
- State/County record detection
- Change tracking with metadata preservation
- Human review interface for flagged items
- Simple CrewAI orchestration with local Ollama models

---

## 2. DATA FORMAT ANALYSIS

### Input File Structure (Based on maclean2024.xlsx)
The Season Summary follows a strict 16-column format (A-P):

| Column | Field | Max Length | Required | Validation Type |
|--------|-------|------------|----------|-----------------|
| A | Zone | 2 | Y | Numeric (1-12) |
| B | Country | 3 | Y | Enum (USA, CAN, MEX) |
| C | State | 3 | Y | State/Province code |
| D | Family | 20 | Y | Taxonomic validation |
| E | Genus | 20 | Y | Taxonomic validation |
| F | Species | 18 | Y | Taxonomic validation |
| G | Sub-species | 16 | N | Taxonomic validation |
| H | County | 20 | Y | Geographic validation |
| I | State Record | 1 | N | Y/N flag |
| J | County Record | 1 | N | Y/N flag |
| K | Specific Location | 50 | Y | Text validation |
| L | First Date | 9 | Y | Date format (dd-mmm-yy) |
| M | Last Date | 9 | N | Date format/range |
| N | Name | 3 | N | Contributor code |
| O | Comments | 120 | N | Free text |
| P | Year | 4 | Y | Year validation |

### Key Validation Rules:
1. **Date Validation**: Dates should be within the last 3 years
2. **Taxonomic Validation**: Family, Genus, Species must be valid Lepidoptera
3. **Geographic Validation**: State/County combinations must be valid
4. **Record Detection**: Check if observation is first for State or County
5. **Character Limits**: Strict adherence to max lengths
6. **Formatting**: No leading/trailing spaces

---

## 3. SYSTEM ARCHITECTURE

### 3.1 Overview
```
┌─────────────────────────────────────────┐
│         Lovable Frontend                 │
│  (Upload, Review, Download Interface)    │
└────────────────┬────────────────────────┘
                 │ REST API
┌────────────────▼────────────────────────┐
│         Python Backend                   │
│  ┌──────────────────────────────────┐   │
│  │     CrewAI Orchestrator          │   │
│  └────────────┬─────────────────────┘   │
│               │                          │
│  ┌────────────▼─────────────────────┐   │
│  │    Validation Agent Crew         │   │
│  │  (16 Specialized Agents)         │   │
│  └────────────┬─────────────────────┘   │
│               │                          │
│  ┌────────────▼─────────────────────┐   │
│  │    External API Integrations     │   │
│  │  • iNaturalist MCP Server        │   │
│  │  • Local Ollama Models           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 3.2 CrewAI Agent Structure

Each agent is responsible for validating one column:

```python
# Agent Configuration Template
class ValidationAgent:
    name: str           # e.g., "ZoneValidator"
    role: str          # e.g., "Zone Number Validator"
    goal: str          # e.g., "Validate zone numbers are 1-12"
    backstory: str     # Context for the agent
    tools: List        # iNat API, Ollama, etc.
    llm: str          # "ollama/llama2" (local)
```

---

## 4. CREWAI AGENT SPECIFICATIONS

### 4.1 Field Validation Agents

#### Agent 1: ZoneValidator
```python
{
    "name": "ZoneValidator",
    "role": "Zone Number Validator",
    "goal": "Validate LepSoc zone numbers (1-12)",
    "validation_rules": [
        "Must be numeric",
        "Range: 1-12",
        "Max length: 2 characters"
    ]
}
```

#### Agent 2: CountryValidator
```python
{
    "name": "CountryValidator",
    "role": "Country Code Validator",
    "goal": "Validate country codes",
    "validation_rules": [
        "Must be: USA, CAN, or MEX",
        "Exactly 3 characters"
    ]
}
```

#### Agent 3: StateValidator
```python
{
    "name": "StateValidator",
    "role": "State/Province Validator",
    "goal": "Validate state/province codes",
    "validation_rules": [
        "Valid US state abbreviations (2 char)",
        "Valid Canadian province codes",
        "Mexican state codes",
        "Cross-reference with Country field"
    ]
}
```

#### Agent 4: FamilyValidator
```python
{
    "name": "FamilyValidator",
    "role": "Taxonomic Family Validator",
    "goal": "Validate Lepidoptera family names",
    "tools": ["inat_mcp_search"],
    "validation_rules": [
        "Must be valid Lepidoptera family",
        "Check against iNaturalist taxonomy",
        "Max 20 characters"
    ]
}
```

#### Agent 5: GenusValidator
```python
{
    "name": "GenusValidator",
    "role": "Taxonomic Genus Validator",
    "goal": "Validate genus names",
    "tools": ["inat_mcp_search"],
    "validation_rules": [
        "Must be valid genus under specified family",
        "Check against iNaturalist taxonomy",
        "Max 20 characters"
    ]
}
```

#### Agent 6: SpeciesValidator
```python
{
    "name": "SpeciesValidator",
    "role": "Species Name Validator",
    "goal": "Validate species epithets",
    "tools": ["inat_mcp_search"],
    "validation_rules": [
        "Valid species under genus",
        "Check full binomial name",
        "Max 18 characters"
    ]
}
```

#### Agent 7: SubspeciesValidator
```python
{
    "name": "SubspeciesValidator",
    "role": "Subspecies Validator",
    "goal": "Validate subspecies names",
    "tools": ["inat_mcp_search"],
    "validation_rules": [
        "Optional field",
        "Validate if present",
        "Max 16 characters"
    ]
}
```

#### Agent 8: CountyValidator
```python
{
    "name": "CountyValidator",
    "role": "County/Region Validator",
    "goal": "Validate county names",
    "tools": ["inat_mcp_places"],
    "validation_rules": [
        "Valid county for state",
        "No 'County' suffix",
        "Max 20 characters"
    ]
}
```

#### Agent 9: StateRecordValidator
```python
{
    "name": "StateRecordValidator",
    "role": "State Record Detector",
    "goal": "Verify if observation is a state record",
    "tools": ["inat_mcp_observations"],
    "validation_rules": [
        "Check historical observations",
        "Y/N/blank only",
        "Cross-verify with iNaturalist"
    ]
}
```

#### Agent 10: CountyRecordValidator
```python
{
    "name": "CountyRecordValidator",
    "role": "County Record Detector",
    "goal": "Verify if observation is a county record",
    "tools": ["inat_mcp_observations"],
    "validation_rules": [
        "Check county-level historical data",
        "Y/N/blank only",
        "Cross-verify with iNaturalist"
    ]
}
```

#### Agent 11: LocationValidator
```python
{
    "name": "LocationValidator",
    "role": "Specific Location Validator",
    "goal": "Validate location descriptions",
    "validation_rules": [
        "Max 50 characters",
        "Check for GPS coordinates",
        "Validate against known places"
    ]
}
```

#### Agent 12: FirstDateValidator
```python
{
    "name": "FirstDateValidator",
    "role": "First Date Validator",
    "goal": "Validate observation start dates",
    "validation_rules": [
        "Format: dd-mmm-yy",
        "Within last 3 years (warning if older)",
        "Not future date",
        "Exactly 9 characters"
    ]
}
```

#### Agent 13: LastDateValidator
```python
{
    "name": "LastDateValidator",
    "role": "Last Date Validator",
    "goal": "Validate observation end dates",
    "validation_rules": [
        "Optional field",
        "Must be >= First Date",
        "Same format as First Date"
    ]
}
```

#### Agent 14: NameValidator
```python
{
    "name": "NameValidator",
    "role": "Contributor Name Validator",
    "goal": "Validate contributor codes",
    "validation_rules": [
        "3-character code",
        "Check against master file",
        "Optional field"
    ]
}
```

#### Agent 15: CommentValidator
```python
{
    "name": "CommentValidator",
    "role": "Comment Field Validator",
    "goal": "Validate comment content",
    "validation_rules": [
        "Max 120 characters",
        "Check for GPS coordinates",
        "Optional field"
    ]
}
```

#### Agent 16: YearValidator
```python
{
    "name": "YearValidator",
    "role": "Year Validator",
    "goal": "Validate observation year",
    "validation_rules": [
        "4-digit year",
        "Within last 3 years (warning if older)",
        "Matches First Date year"
    ]
}
```

---

## 5. CREWAI IMPLEMENTATION

### 5.1 Simple CrewAI Structure
```python
# crew.py - Main CrewAI Implementation
from crewai import Agent, Crew, Task
from langchain.llms import Ollama
import pandas as pd
from typing import List, Dict, Any

class LepSocValidationCrew:
    def __init__(self):
        # Initialize local Ollama
        self.llm = Ollama(model="llama2", base_url="http://localhost:11434")
        
        # Create validation agents
        self.agents = self._create_agents()
        
        # Initialize iNat MCP client
        self.inat_client = self._init_inat_client()
    
    def _create_agents(self) -> List[Agent]:
        """Create one agent per column"""
        agents = []
        
        # Zone Validator
        agents.append(Agent(
            role='Zone Validator',
            goal='Validate zone numbers are between 1-12',
            backstory='Expert in LepSoc geographic zones',
            llm=self.llm,
            allow_delegation=False
        ))
        
        # Country Validator
        agents.append(Agent(
            role='Country Code Validator',
            goal='Validate country codes (USA, CAN, MEX)',
            backstory='Expert in North American country codes',
            llm=self.llm,
            allow_delegation=False
        ))
        
        # ... (continue for all 16 agents)
        
        return agents
    
    def validate_row(self, row: pd.Series) -> Dict[str, Any]:
        """Validate a single row of data"""
        validation_results = {
            'row_number': row.name,
            'errors': [],
            'warnings': [],
            'corrections': {},
            'metadata': {}
        }
        
        # Create tasks for each field
        tasks = []
        for i, agent in enumerate(self.agents):
            field_name = row.index[i]
            field_value = row.iloc[i]
            
            task = Task(
                description=f'Validate {field_name}: {field_value}',
                agent=agent,
                expected_output='Validation result with any corrections'
            )
            tasks.append(task)
        
        # Execute crew
        crew = Crew(
            agents=self.agents,
            tasks=tasks,
            verbose=True
        )
        
        results = crew.kickoff()
        
        # Process results
        for result in results:
            if result.get('error'):
                validation_results['errors'].append(result)
            if result.get('warning'):
                validation_results['warnings'].append(result)
            if result.get('correction'):
                validation_results['corrections'][result['field']] = result['correction']
        
        return validation_results
    
    def validate_file(self, filepath: str) -> pd.DataFrame:
        """Validate entire Excel/CSV file"""
        df = pd.read_excel(filepath) if filepath.endswith('.xlsx') else pd.read_csv(filepath)
        
        all_results = []
        for index, row in df.iterrows():
            result = self.validate_row(row)
            all_results.append(result)
            
            # Human-in-the-loop checkpoint
            if result['errors'] or result['warnings']:
                print(f"Row {index} needs review: {result}")
                # Here would be the interface for human review
        
        return self._apply_corrections(df, all_results)
```

### 5.2 iNaturalist Integration
```python
# inat_tools.py - iNaturalist MCP Integration
from mcp import ClientSession
from mcp.client.sse import sse_client
import asyncio

class INatValidator:
    def __init__(self, server_url="http://localhost:8811/sse"):
        self.server_url = server_url
    
    async def validate_species(self, family, genus, species):
        """Validate taxonomic name against iNaturalist"""
        async with sse_client(self.server_url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Search for the species
                full_name = f"{genus} {species}"
                result = await session.call_tool("search_species", {
                    "query": full_name,
                    "limit": 1
                })
                
                if result['results']:
                    taxon = result['results'][0]
                    # Verify family matches
                    if family.lower() not in taxon.get('ancestry', '').lower():
                        return {'valid': False, 'error': 'Family mismatch'}
                    return {'valid': True, 'taxon_id': taxon['taxon_id']}
                
                return {'valid': False, 'error': 'Species not found'}
    
    async def check_state_record(self, taxon_id, state):
        """Check if this is a state record"""
        result = await session.call_tool("count_observations", {
            "taxon_id": taxon_id,
            "place_name": state,
            "quality_grade": "research"
        })
        
        # If count is 0, it's a new state record
        return result['total_results'] == 0
    
    async def check_county_record(self, taxon_id, state, county):
        """Check if this is a county record"""
        place_name = f"{county}, {state}"
        result = await session.call_tool("count_observations", {
            "taxon_id": taxon_id,
            "place_name": place_name,
            "quality_grade": "research"
        })
        
        return result['total_results'] == 0
```

---

## 6. LOVABLE FRONTEND INSTRUCTIONS

### 6.1 Frontend Requirements

Create a React application with the following components:

```jsx
// App Structure
src/
├── components/
│   ├── FileUpload.jsx       // Excel/CSV upload
│   ├── ValidationStatus.jsx // Progress indicator
│   ├── ReviewTable.jsx      // Human review interface
│   ├── MetadataViewer.jsx   // Show changes/corrections
│   └── DownloadResults.jsx  // Export validated file
├── api/
│   └── validationApi.js     // Backend communication
└── App.jsx
```

### 6.2 Key Features to Implement

1. **File Upload Component**
```jsx
// Accept .xlsx, .csv files
// Max size: 10MB
// Show preview of first 10 rows
// Validate column headers match expected format
```

2. **Validation Progress**
```jsx
// Real-time progress bar
// Row-by-row status updates
// Error/warning counters
// Estimated time remaining
```

3. **Human Review Interface**
```jsx
// Paginated table of flagged rows
// Highlight errors in red, warnings in yellow
// Edit capability for corrections
// Accept/Reject/Modify buttons
// Add review notes
```

4. **API Integration**
```javascript
// Backend endpoints:
POST /api/validate/upload     // Upload file
GET  /api/validate/status/{id} // Check progress
GET  /api/validate/review/{id} // Get items for review
POST /api/validate/approve/{id} // Approve corrections
GET  /api/validate/download/{id} // Download results
```

### 6.3 UI/UX Requirements
- Clean, professional interface
- Responsive design
- Clear error messages
- Tooltips for field descriptions
- Keyboard shortcuts for review actions
- Export options (Excel, CSV, JSON)

---

## 7. BACKEND API SPECIFICATION

### 7.1 REST API Endpoints

```python
# FastAPI Backend Structure
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import uuid

app = FastAPI()

@app.post("/api/validate/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload Excel/CSV file for validation
    Returns: validation_id
    """
    validation_id = str(uuid.uuid4())
    # Save file, start validation
    return {"validation_id": validation_id, "status": "processing"}

@app.get("/api/validate/status/{validation_id}")
async def get_status(validation_id: str):
    """
    Get validation progress
    Returns: progress percentage, errors, warnings
    """
    return {
        "status": "processing",
        "progress": 45,
        "total_rows": 1000,
        "processed_rows": 450,
        "errors": 12,
        "warnings": 23
    }

@app.get("/api/validate/review/{validation_id}")
async def get_review_items(validation_id: str, page: int = 1):
    """
    Get flagged items for human review
    """
    return {
        "items": [...],
        "total": 35,
        "page": page
    }

@app.post("/api/validate/approve/{validation_id}")
async def approve_corrections(validation_id: str, corrections: dict):
    """
    Apply human-approved corrections
    """
    # Apply corrections to data
    return {"status": "corrections_applied"}

@app.get("/api/validate/download/{validation_id}")
async def download_results(validation_id: str):
    """
    Download validated file with metadata
    """
    return FileResponse(
        path=f"/results/{validation_id}_validated.xlsx",
        filename="validated_season_summary.xlsx"
    )
```

### 7.2 WebSocket for Real-time Updates
```python
@app.websocket("/ws/{validation_id}")
async def websocket_endpoint(websocket: WebSocket, validation_id: str):
    await websocket.accept()
    while True:
        # Send progress updates
        await websocket.send_json({
            "type": "progress",
            "row": current_row,
            "status": "validating",
            "field": "Species"
        })
```

---

## 8. METADATA TRACKING

### 8.1 Change Tracking Structure
```python
metadata = {
    "validation_id": "uuid",
    "original_file": "maclean2024.xlsx",
    "validation_date": "2024-11-10",
    "total_rows": 1000,
    "changes": [
        {
            "row": 15,
            "field": "Species",
            "original": "plexipus",
            "corrected": "plexippus",
            "reason": "Spelling correction",
            "confidence": 0.95,
            "validated_by": "iNaturalist"
        }
    ],
    "new_records": {
        "state_records": [
            {"row": 45, "species": "Danaus plexippus", "state": "AK"}
        ],
        "county_records": [
            {"row": 67, "species": "Actias luna", "county": "Door", "state": "WI"}
        ]
    },
    "validation_stats": {
        "errors_found": 23,
        "warnings_issued": 45,
        "auto_corrections": 18,
        "human_reviews": 5
    }
}
```

### 8.2 Output File Structure
The validated file will include:
- All original columns (A-P)
- Additional metadata columns:
  - Q: Validation_Status (PASS/FAIL/CORRECTED)
  - R: Validation_Notes
  - S: Original_Value (if corrected)
  - T: Confidence_Score
  - U: Validated_By (Agent/Human)

---

## 9. SPRINT PLAN

### Sprint 1: Foundation (Week 1)
**Goal:** Set up project infrastructure and basic validation framework

**Tasks:**
1. **Environment Setup (Day 1)**
   - Set up Python project with CrewAI, FastAPI
   - Install and configure local Ollama
   - Set up iNaturalist MCP server
   - Initialize Git repository

2. **Data Model & Database (Day 2)**
   - Create data models for validation results
   - Set up SQLite for metadata storage
   - Design change tracking schema
   - Create file upload/storage system

3. **Basic CrewAI Structure (Day 3-4)**
   - Implement base ValidationAgent class
   - Create first 3 simple validators (Zone, Country, State)
   - Set up CrewAI orchestrator
   - Test with sample data

4. **API Foundation (Day 5)**
   - Implement upload endpoint
   - Create basic validation pipeline
   - Add status checking endpoint
   - Unit tests for validators

**Deliverables:**
- Working project structure
- 3 basic validators operational
- File upload and processing pipeline

---

### Sprint 2: Core Validators (Week 2)
**Goal:** Implement all field validators and iNaturalist integration

**Tasks:**
1. **Taxonomic Validators (Day 1-2)**
   - Implement Family, Genus, Species validators
   - Integrate with iNaturalist MCP API
   - Add caching for API responses

2. **Geographic Validators (Day 3)**
   - Implement County validator
   - Add State/County combination validation
   - Integrate with iNat places API

3. **Record Detection (Day 4)**
   - Implement State Record detector
   - Implement County Record detector
   - Historical data comparison logic

4. **Remaining Validators (Day 5)**
   - Date validators (First/Last)
   - Year, Name, Comment, Location validators
   - Integration testing all validators

**Deliverables:**
- All 16 validators implemented
- iNaturalist integration working
- Record detection functional

---

### Sprint 3: Frontend Development (Week 3)
**Goal:** Build Lovable frontend interface

**Tasks:**
1. **Project Setup (Day 1)**
   - Initialize Lovable project
   - Set up component structure
   - Configure API client

2. **Upload & Progress (Day 2)**
   - File upload component
   - Progress tracking UI
   - WebSocket integration

3. **Review Interface (Day 3-4)**
   - Review table component
   - Edit capabilities
   - Approve/reject workflow
   - Keyboard shortcuts

4. **Results & Export (Day 5)**
   - Metadata viewer
   - Download component
   - Export format options

**Deliverables:**
- Complete frontend application
- All UI components functional
- Backend integration complete

---

### Sprint 4: Human-in-the-Loop & Polish (Week 4)
**Goal:** Implement review workflow and system refinement

**Tasks:**
1. **Review Workflow (Day 1-2)**
   - Human review queue system
   - Correction approval process
   - Review history tracking

2. **Metadata & Reporting (Day 3)**
   - Complete metadata tracking
   - Generate validation reports
   - Statistics dashboard

3. **Performance Optimization (Day 4)**
   - Batch processing optimization
   - API response caching
   - Parallel validation execution

4. **Testing & Documentation (Day 5)**
   - End-to-end testing
   - User documentation
   - API documentation
   - Deployment guide

**Deliverables:**
- Complete human review system
- Performance optimized
- Full documentation

---

### Sprint 5: Testing & Deployment (Week 5)
**Goal:** Final testing, bug fixes, and production deployment

**Tasks:**
1. **Integration Testing (Day 1-2)**
   - Full workflow testing
   - Edge case handling
   - Load testing

2. **Bug Fixes (Day 3)**
   - Address identified issues
   - UI/UX refinements
   - Performance tweaks

3. **Deployment Prep (Day 4)**
   - Docker containerization
   - Environment configuration
   - Deployment scripts

4. **Launch (Day 5)**
   - Production deployment
   - User training materials
   - Monitoring setup

**Deliverables:**
- Production-ready system
- Deployed application
- Training materials

---

## 10. DEVELOPMENT PRIORITIES

### Must Have (MVP)
1. All 16 field validators
2. iNaturalist species/location validation
3. Basic human review interface
4. File upload/download
5. Change tracking

### Should Have
1. Real-time progress updates
2. Batch processing
3. Historical comparison for records
4. Detailed error reporting
5. Export formats (Excel, CSV, JSON)

### Nice to Have
1. Advanced statistics dashboard
2. Validation rule customization
3. Multi-file batch processing
4. API for external integration
5. Audit trail

---

## 11. TECHNICAL DEPENDENCIES

```yaml
# requirements.txt
crewai==0.1.0
langchain==0.1.0
ollama==0.1.0
fastapi==0.104.0
uvicorn==0.24.0
pandas==2.1.0
openpyxl==3.1.0
sqlalchemy==2.0.0
pydantic==2.4.0
httpx==0.25.0
websockets==11.0.0

# For iNat MCP integration
mcp==0.1.0
asyncio==3.4.0
```

---

## 12. SUCCESS CRITERIA

1. **Accuracy**: 99% validation accuracy for taxonomic names
2. **Performance**: Process 1000 rows in < 5 minutes
3. **Reliability**: < 0.1% false positive rate for record detection
4. **Usability**: < 5 clicks to complete review workflow
5. **Completeness**: 100% of fields validated

---

## APPENDIX A: SAMPLE VALIDATION OUTPUT

```json
{
  "row_15": {
    "status": "CORRECTED",
    "original": {
      "Species": "plexipus"
    },
    "corrected": {
      "Species": "plexippus"
    },
    "validation_details": {
      "Species": {
        "status": "CORRECTED",
        "confidence": 0.95,
        "validator": "SpeciesValidator",
        "inat_taxon_id": 48662,
        "message": "Species name corrected based on iNaturalist taxonomy"
      }
    },
    "is_state_record": false,
    "is_county_record": true,
    "metadata": {
      "validated_at": "2024-11-10T10:30:45Z",
      "validation_method": "automated",
      "requires_review": false
    }
  }
}
```

---

## APPENDIX B: ERROR CODES

| Code | Description | Action Required |
|------|-------------|-----------------|
| E001 | Invalid Zone Number | Correct to 1-12 |
| E002 | Invalid Country Code | Use USA/CAN/MEX |
| E003 | Species Not Found | Manual review |
| E004 | Invalid Date Format | Format as dd-mmm-yy |
| E005 | Date Out of Range | Check if < 3 years |
| E006 | County Not Found | Verify spelling |
| E007 | State/County Mismatch | Check geographic data |
| E008 | Character Limit Exceeded | Truncate or abbreviate |
| E009 | Required Field Missing | Provide value |
| E010 | Taxonomic Inconsistency | Review hierarchy |

---

**End of Specification Document**

This specification provides a complete blueprint for implementing the LepSoc Season Summary Validation System using CrewAI agents, iNaturalist integration, and a modern web interface.

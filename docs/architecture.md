# LepSox System Architecture

## Overview

LepSox is a modular validation system for Lepidopterist Society observation data. It uses CrewAI to orchestrate 16 specialized validation agents, each responsible for validating one column of the input data.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                           │
│  (CLI Script or FastAPI Web Interface - Future)             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              LepSocValidationCrew (Orchestrator)             │
│  • Reads Excel/CSV files                                     │
│  • Coordinates 16 validation agents                          │
│  • Applies corrections                                       │
│  • Generates output with metadata                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                ┌──────────┴──────────┐
                ▼                     ▼
┌───────────────────────┐   ┌─────────────────────┐
│  Validation Agents    │   │  External Services  │
│  • Geographic (4)     │   │  • Ollama LLM       │
│  • Taxonomic (4)      │   │  • iNaturalist API  │
│  • Temporal (3)       │   │                     │
│  • Records (2)        │   │                     │
│  • Metadata (3)       │   │                     │
└───────────────────────┘   └─────────────────────┘
```

## Component Details

### 1. Entry Point

**Location**: `scripts/run_validator.py`

Simple CLI script that:
- Accepts input/output file paths
- Creates `LepSocValidationCrew` instance
- Runs validation
- Saves results

### 2. Orchestrator

**Location**: `src/lepsox/validator.py`

**Class**: `LepSocValidationCrew`

**Responsibilities**:
- Initialize all 16 validation agents
- Read Excel/CSV input files
- Process rows sequentially
- Collect validation results
- Apply corrections
- Add metadata columns
- Write output files
- Print summary statistics

**Key Methods**:
```python
def validate_row(row_index, row_data) -> Dict
    # Validates single row with all agents

def validate_file(filepath, output_path) -> DataFrame
    # Validates entire file and saves results

def _apply_corrections(df, results) -> DataFrame
    # Applies corrections and adds metadata columns

def _print_summary(results)
    # Prints validation statistics
```

### 3. Validation Agents

**Location**: `src/lepsox/agents/`

All agents inherit from `BaseValidator` which extends `crewai.Agent`.

#### Agent Categories:

**Geographic Validators** (`geographic.py`):
- `ZoneValidator` - Zones 1-12
- `CountryValidator` - USA/CAN/MEX
- `StateValidator` - State/province codes
- `CountyValidator` - County names

**Taxonomic Validators** (`taxonomic.py`):
- `FamilyValidator` - Lepidoptera families
- `GenusValidator` - Genus names
- `SpeciesValidator` - Species epithets
- `SubspeciesValidator` - Subspecies (optional)

**Temporal Validators** (`temporal.py`):
- `FirstDateValidator` - Start dates (dd-mmm-yy)
- `LastDateValidator` - End dates (optional)
- `YearValidator` - Observation years

**Record Validators** (`records.py`):
- `StateRecordValidator` - State-level new records
- `CountyRecordValidator` - County-level new records

**Metadata Validators** (`metadata.py`):
- `LocationValidator` - Specific location text
- `NameValidator` - Contributor codes
- `CommentValidator` - Comments field

#### Validation Flow:

```python
1. Agent receives field value + full row data
2. Checks required/optional status
3. Validates format/length/content
4. Checks against rules (ranges, codes, etc.)
5. Returns ValidationResult with:
   - is_valid: bool
   - errors: List[str]
   - warnings: List[str]
   - correction: Optional value
   - metadata: Dict (e.g., needs_inat_check)
```

### 4. Data Models

**Location**: `src/lepsox/models/`

**ValidationResult** (`validation_result.py`):
- Standardized container for validation results
- Used by all validators
- Converted to dict for aggregation

### 5. External Integrations

**Location**: `src/lepsox/integrations/`

**INatValidator** (`inat.py`):
- Connects to iNaturalist MCP server
- Methods:
  - `check_species(genus, species)` - Validate taxonomy
  - `check_location(county, state, country)` - Validate geography
  - `check_record_status(taxon_id, place_id)` - Detect new records

**Future**: Sprint 2 will integrate iNat calls into relevant validators.

### 6. Configuration

**Location**: `src/lepsox/config.py`

Centralized configuration for:
- Server URLs (Ollama, iNat MCP)
- Validation constants (zones, countries, states)
- Column names
- Common families
- Date formats

### 7. Tests

**Location**: `tests/`

- `conftest.py` - Pytest fixtures
- `test_agents.py` - Unit tests for validators
- `fixtures/` - Sample data files

## Data Flow

### Input
1. Excel/CSV file with 16 columns (A-P)
2. No headers (raw data only)
3. Column order must match spec

### Processing
1. Read file into Pandas DataFrame
2. Assign column names from config
3. For each row:
   - Pass to all 16 validators
   - Collect results
   - Flag for review if needed
4. Apply automatic corrections
5. Add 5 metadata columns (Q-U)

### Output
Original 16 columns + 5 metadata columns:
- Q: `Validation_Status` (PASS/CORRECTED/FAIL)
- R: `Validation_Notes` (error/warning messages)
- S: `Original_Values` (what was changed)
- T: `Confidence_Score` (1.0/0.8/0.5)
- U: `Validated_By` (CrewAI Agent)

## Technology Stack

### Core
- **Python 3.9+**
- **CrewAI 0.28.8** - Agent orchestration
- **Langchain** - LLM integration
- **Pandas** - Data processing
- **OpenPyXL** - Excel file handling

### AI/ML
- **Ollama** - Local LLM (llama2)
- **iNaturalist MCP** - Species/location data

### Development
- **Pytest** - Testing
- **Black** - Code formatting
- **MyPy** - Type checking
- **Loguru** - Logging

## Deployment

### Current (Sprint 1)
- Run locally via CLI script
- Manual file upload/download
- Results saved to disk

### Future (Sprint 3+)
- FastAPI web service
- Browser-based file upload
- Real-time progress updates
- Docker containerization

## Performance Considerations

### Current Bottlenecks
1. **Sequential processing** - Rows processed one at a time
2. **LLM calls** - Ollama invoked for each agent (may be unnecessary)
3. **No caching** - Repeat validations not cached

### Optimization Opportunities (Sprint 4)
1. Batch row processing
2. Remove LLM calls from simple validators (Zone, Country, etc.)
3. Cache common lookups (families, state/county lists)
4. Parallel agent execution per row
5. iNaturalist response caching

## Security

### Current
- No authentication
- Local execution only
- No sensitive data handling

### Future
- File upload size limits
- Input sanitization
- Rate limiting for API calls
- User authentication (if web-based)

## Extensibility

### Adding New Validators
1. Create new validator class inheriting from `BaseValidator`
2. Implement `validate(value, row_data)` method
3. Add to agent list in `LepSocValidationCrew._create_validators()`
4. Update column names in config if needed

### Adding New Integrations
1. Create module in `src/lepsox/integrations/`
2. Implement async methods
3. Add configuration to `config.py`
4. Use in relevant validators

## Monitoring & Logging

### Current
- Console output (print statements)
- Summary statistics after validation

### Planned
- Structured logging with Loguru
- Progress tracking
- Error rate monitoring
- Performance metrics

## Testing Strategy

### Unit Tests
- Each validator tested independently
- Mock LLM calls
- Test edge cases (empty, invalid, boundary values)

### Integration Tests
- Full file validation
- Multiple rows with varied data
- Error correction flow

### Fixtures
- `valid_sample.xlsx` - Clean reference data
- `test_with_errors.xlsx` - Known errors for testing

## Version History

**v0.1.0** (Current)
- Initial modular architecture
- 16 validation agents
- Basic CLI interface
- Excel/CSV I/O
- Test framework

---

*Last Updated: November 2024*
*Sprint: 0 (Pre-Sprint Setup)*

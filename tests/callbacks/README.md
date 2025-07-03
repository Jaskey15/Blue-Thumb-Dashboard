# Callback Testing Guide

This directory contains tests for the Blue Thumb Dashboard callback functions. The testing approach focuses on **logic testing** rather than full Dash app integration, making tests faster, more reliable, and easier to maintain.

## Testing Philosophy

### Why Test Callbacks?

Callbacks contain the core business logic of your Dash application:
- **State management** across multiple tabs
- **Navigation logic** from map clicks
- **Data validation and filtering**
- **Error handling**
- **UI state coordination**

Testing these ensures reliability as your application grows.

### Testing Approach

We use a **hybrid approach** that combines:

1. **Logic Testing** - Test the core logic functions directly
2. **Component Testing** - Test individual pieces of callback logic
3. **Integration Testing** - Test how multiple pieces work together
4. **Error Handling Testing** - Test edge cases and error scenarios

## File Structure

```
tests/callbacks/
├── __init__.py                          # Package initialization
├── conftest.py                          # Shared fixtures
├── README.md                            # This documentation
├── test_shared_callbacks_simple.py     # Working example tests
└── test_shared_callbacks.py            # Advanced integration tests (WIP)
```

## Testing Patterns

### 1. Logic Testing Pattern

Test the core logic without Dash integration:

```python
def test_site_name_extraction_from_click_data(self):
    """Test extracting site name from map click data."""
    click_data = {
        'points': [{
            'text': '<b>Site:</b> Test Site<br>Parameter: 8.2 mg/L'
        }]
    }
    
    hover_text = click_data['points'][0]['text']
    site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
    assert site_name == 'Test Site', "Should extract site name correctly"
```

### 2. Parameter Detection Pattern

Test parameter type identification:

```python
def test_parameter_type_detection(self):
    """Test parameter type detection logic."""
    # Test chemical parameters
    chemical_params = ['chem:pH', 'chem:do_percent', 'chem:Phosphorus']
    for param in chemical_params:
        assert param.startswith('chem:'), f"Should detect chemical parameter: {param}"
```

### 3. Navigation Data Structure Pattern

Test navigation data formats:

```python
def test_navigation_data_structures(self):
    """Test navigation data structure formats."""
    habitat_data = {
        'target_tab': 'habitat-tab',
        'target_site': 'Test Site',
        'source_parameter': 'habitat:Habitat_Score'
    }
    
    assert 'target_tab' in habitat_data, "Should contain target_tab"
    assert 'target_site' in habitat_data, "Should contain target_site"
```

### 4. Error Handling Pattern

Test error scenarios:

```python
def test_malformed_click_data_handling(self):
    """Test handling of malformed click data."""
    malformed_data = {'points': [{}]}  # Missing text field
    
    try:
        hover_text = malformed_data['points'][0]['text']
        extraction_failed = False
    except KeyError:
        extraction_failed = True
    
    assert extraction_failed is True, "Should fail gracefully with malformed data"
```

### 5. Integration Testing Pattern

Test complete workflows:

```python
def test_complete_habitat_navigation_flow(self):
    """Test complete habitat navigation scenario."""
    # Input validation
    click_data = {...}
    current_parameter = 'habitat:Habitat_Score'
    
    # Processing logic
    hover_text = click_data['points'][0]['text']
    site_name = hover_text.split('<br>')[0].replace('<b>Site:</b> ', '')
    
    # Navigation logic
    if current_parameter == 'habitat:Habitat_Score':
        target_tab = "habitat-tab"
        nav_data = {
            'target_tab': 'habitat-tab',
            'target_site': site_name,
            'source_parameter': current_parameter
        }
    
    # Verification
    assert target_tab == "habitat-tab", "Should navigate to habitat tab"
```

## What We Test

### ✅ Currently Tested

#### **shared_callbacks** (12 tests)
- **Modal Logic**: Attribution and image credits modal toggling
- **Site Name Extraction**: Parsing click data to extract site names
- **Parameter Type Detection**: Identifying chemical, biological, and habitat parameters
- **Parameter Mapping**: Converting biological parameters to community types
- **Navigation Data Structures**: Ensuring correct data format for navigation
- **Trigger Identification**: Extracting trigger IDs from callback context
- **Error Handling**: Malformed data, missing data, and edge cases
- **Integration Flows**: Complete navigation scenarios

#### **habitat_callbacks** (22 tests)
- **State Management**: Tab state saving and restoration logic
- **Dropdown Population**: Site filtering and option creation with sorting
- **Navigation Integration**: Map clicks → tab navigation with priority handling
- **Content Display Logic**: Site validation and content rendering
- **Error Handling**: Empty sites, invalid navigation, malformed data
- **State Restoration**: Priority logic between navigation and saved state
- **Integration Workflows**: Complete map-to-content user flows

### 📋 To Be Tested (remaining callbacks)

- **overview_callbacks**: Map visualization and parameter selection
- **chemical_callbacks**: Complex filtering, multiple controls, time series
- **biological_callbacks**: Community selection, gallery navigation
- **Gallery Navigation**: Species gallery functionality

## Running Tests

### Common Test Commands

```bash
# Run all callback tests with verbose output
pytest tests/callbacks -v

# Run with coverage report
pytest tests/callbacks --cov=callbacks --cov-report=term-missing --cov-report=html

# Run specific test file
pytest tests/callbacks/test_shared_callbacks.py -v

# Run specific test class
pytest tests/callbacks/test_shared_callbacks.py::TestNavigationLogic -v

# Run single test
pytest tests/callbacks/test_shared_callbacks.py::TestNavigationLogic::test_site_name_extraction_from_click_data -v

# Stop on first failure
pytest tests/calls -x

# Run only failed tests from last run
pytest tests/callbacks --lf

# Run tests in parallel (if pytest-xdist installed)
pytest tests/callbacks -n auto

# Show local variables in tracebacks
pytest tests/callbacks -v --showlocals
```

### Working Directory
Always run tests from the project root directory (where `callbacks/` folder exists).

### Test Output
- Use `-v` for verbose output showing each test
- Use `-q` for minimal output
- Use `--tb=short` for shorter tracebacks
- Use `--showlocals` to see local variables in failures

### Coverage Reports
Running with coverage (`--cov`) will:
1. Show terminal report of missed lines
2. Generate HTML report in htmlcov/index.html
3. Help identify untested code paths

## Test Organization

### Test Classes by Functionality

- **TestModalLogic**: Modal toggle functionality
- **TestNavigationLogic**: Navigation and parameter logic
- **TestErrorHandling**: Error scenarios and edge cases
- **TestIntegrationScenarios**: End-to-end workflows

### Naming Conventions

- **Test files**: `test_[module_name].py`
- **Test classes**: `Test[Functionality]`
- **Test methods**: `test_[specific_behavior]`

## Benefits of This Approach

### ✅ Advantages

1. **Fast Execution**: No Dash app startup overhead
2. **Reliable**: No complex mocking of Dash internals
3. **Focused**: Tests specific logic without UI complexity
4. **Maintainable**: Easy to understand and modify
5. **Comprehensive**: Can test edge cases easily

### ⚠️ Limitations

1. **No UI Integration**: Doesn't test actual Dash callback registration
2. **No Browser Testing**: No Selenium-based testing
3. **Mock Limitations**: External dependencies need mocking

## Next Steps

1. **Create tests for other callback modules**:
   - `test_overview_callbacks.py`
   - `test_chemical_callbacks.py`
   - `test_biological_callbacks.py`
   - `test_habitat_callbacks.py`

2. **Add integration tests** for critical user flows

3. **Set up continuous integration** to run tests automatically

4. **Add performance tests** for data-heavy operations

## Example Commands

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run all tests with verbose output
pytest tests/callbacks/ -v

# Run tests with coverage report
pytest tests/callbacks/ --cov=callbacks --cov-report=term-missing

# Run only failed tests from last run
pytest tests/callbacks/ --lf

# Run tests in parallel (if pytest-xdist installed)
pytest tests/callbacks/ -n auto
```

## Contributing

When adding new callback tests:

1. Follow the established patterns in `test_shared_callbacks_simple.py`
2. Focus on testing logic rather than Dash integration
3. Include error handling tests
4. Add integration tests for complex workflows
5. Document any new testing patterns in this README 
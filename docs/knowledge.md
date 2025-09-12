# Documentation Knowledge

## Documentation Structure

### Memory Bank (`memory-bank/`)
Persistent knowledge files that capture project context:
- **projectbrief.md**: High-level project overview and goals
- **techContext.md**: Technical architecture and key components
- **systemPatterns.md**: Common patterns and design principles
- **activeContext.md**: Current development context
- **productContext.md**: Product requirements and features
- **progress.md**: Development progress tracking

### Sprint Documentation (`sprint/`)
Detailed sprint planning and execution records:
- **01_first_sprint.md**: Initial FastAPI scaffold setup
- **02_generic_crawl.md**: Generic crawling endpoint implementation
- **03_retry_and_proxy.md**: Retry logic and proxy support
- **04_proxy_wiring_and_health.md**: Proxy health tracking
- **05_refactoring_reuse.md**: Code refactoring for reusability
- **06_camoufox_user_data_and_additional_stealth.md**: User data persistence
- **07_dpd_tracking_endpoint.md**: DPD-specific crawling
- **08_html_length_validation_and_retry.md**: Content validation
- **09_integration_tests_for_crawl.md**: Testing strategy
- **10_auspost_tracking_endpoint.md**: AusPost crawling with humanization
- **11_convert_to_OOP.md**: Object-oriented refactoring
- **12_simplify_crawl_endpoint.md**: API simplification
- **13_aupost_robust.md**: AusPost robustness improvements
- **14_dpd_base_url_update.md**: DPD URL updates
- **15_geoip_auto_enable.md**: Automatic GeoIP configuration
- **16_global_logging.md**: Centralized logging implementation
- **17_improve_auspost.md**: AusPost enhancements
- **18_camoufox_user_data_spec.md**: User data specification
- **19_browse_endpoint_spec.md**: Interactive browsing specification
- **20_refactor_services.md**: Service layer refactoring
- **21_tiktok_session_endpoint.md**: TikTok session management
- **22_tiktok_search_endpoint.md**: TikTok search functionality

### Specifications (`specs/`)
Detailed feature specifications:
- **021-tiktok-session-endpoint/**: Complete TikTok session feature spec
  - **contracts/**: API contracts and schemas
  - **data-model.md**: Data structure definitions
  - **plan.md**: Implementation plan
  - **quickstart.md**: Quick setup guide
  - **research.md**: Research findings
  - **tasks.md**: Task breakdown

### Templates (`templates/`)
Standardized templates for consistency:
- **agent-file-template.md**: Template for agent-specific files
- **plan-template.md**: Template for implementation plans
- **spec-template.md**: Template for feature specifications
- **tasks-template.md**: Template for task breakdowns

## Sprint Methodology

### Sprint Structure
Each sprint follows a consistent pattern:
1. **Problem Statement**: Clear definition of what needs to be solved
2. **Solution Overview**: High-level approach to the problem
3. **Implementation Details**: Specific technical changes
4. **Testing Strategy**: How to verify the implementation
5. **Configuration**: Environment and setup requirements
6. **Documentation**: User-facing documentation updates

### Documentation Standards

#### Sprint Documentation Format
```markdown
# Sprint [Number]: [Title]

## Problem
[Clear problem statement]

## Solution
[High-level solution approach]

## Implementation
[Detailed technical implementation]

## Testing
[Testing approach and validation]

## Configuration
[Environment setup and configuration]

## Documentation
[User documentation updates]
```

#### Specification Format
```markdown
# [Feature Name] Specification

## Overview
[Feature overview and purpose]

## Requirements
[Functional and non-functional requirements]

## API Design
[Endpoint definitions and schemas]

## Implementation Plan
[Step-by-step implementation plan]

## Testing Strategy
[Comprehensive testing approach]
```

### Knowledge Management

#### Memory Bank Updates
- **projectbrief.md**: Updated when project scope changes
- **techContext.md**: Updated when architecture evolves
- **systemPatterns.md**: Updated when new patterns emerge
- **progress.md**: Updated after each sprint completion

#### Context Preservation
- Each sprint builds on previous knowledge
- Key decisions documented for future reference
- Architectural patterns captured for reuse
- Configuration examples preserved

### Feature Development Process

#### 1. Research Phase
- Document findings in `research.md`
- Identify technical constraints and requirements
- Explore existing solutions and patterns

#### 2. Specification Phase
- Create detailed spec in `specs/` directory
- Define API contracts and data models
- Plan implementation steps

#### 3. Implementation Phase
- Follow sprint documentation format
- Document configuration changes
- Update relevant knowledge files

#### 4. Testing Phase
- Implement comprehensive test coverage
- Document testing strategy
- Verify integration with existing features

#### 5. Documentation Phase
- Update user-facing documentation
- Capture lessons learned
- Update architectural knowledge

## Documentation Best Practices

### Writing Standards
- Use clear, concise language
- Include practical examples
- Document configuration options
- Explain architectural decisions

### Maintenance
- Keep documentation synchronized with code
- Update examples when APIs change
- Archive obsolete documentation
- Regular knowledge base reviews

### Templates Usage
- Use templates for consistency
- Customize templates for specific needs
- Update templates based on experience
- Share templates across team

## Knowledge Evolution

### Continuous Improvement
- Regular retrospectives on documentation quality
- Feedback incorporation from users
- Knowledge gap identification and filling
- Process refinement based on experience

### Version Control
- All documentation version controlled
- Clear commit messages for documentation changes
- Branching strategy for major documentation updates
- Review process for significant changes

### Knowledge Sharing
- Documentation accessible to all team members
- Regular knowledge sharing sessions
- Cross-referencing between related documents
- Clear navigation and organization
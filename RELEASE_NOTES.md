### Version 1.1.2
__Changes__
- Fix bug in circularization of contigs report
- Lowered hard limit on long reads from 10 GBase to 1 GBase

### Version 1.1.1
__Changes__
- Include more stats in templated report, as well as cleaned up log
- Updated to Unicycler 0.4.8; use conda version for SPAdes compatibility
- Updated to SPAdes 3.15.3; new download URL
- Updated to RACON 1.4.21
- Updated to Pilon 1.24

### Version 1.1.0
__Changes__
- Updated to SPAdes 3.15.2
- Report circularization of contigs, using templated report
- Set hard limit (10 GBase) on long reads, to avoid unnecessary computation on bad data

### Version 1.0.1
__Changes__
- exposed Unicycler --no_correct option (default: true, as recommended by Torben Nielsen)

### Version 1.0.0
__Changes__
- initial version, forked from kb_SPAdes 1.2.5

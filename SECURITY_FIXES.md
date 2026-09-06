# Security fixes in this version

Fixed the authorization gaps found during review:

1. Doctor appointment lists are scoped to the logged-in doctor.
2. Doctor appointment detail/status routes reject appointments belonging to another doctor with HTTP 403.
3. Doctor patient-profile access is limited to patients who have an appointment with that doctor.
4. Termux requirements no longer explicitly install Pillow or qrcode.

Verification:
- All Python files were compiled with Python's compileall.
- Added three focused regression tests for the access-control fixes.
- The archive was rebuilt after the fixes.

Note: full integration tests still depend on the project's configured runtime/database environment.

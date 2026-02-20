# Errs

**Path:** `backend/errs/`
**Purpose:** Centralized error handling definitions

## Overview

The `backend/errs/` folder provides a centralized location for defining and handling errors within the backend application. It defines common error types as sentinel values and provides a custom `ApiErr` struct for encapsulating error details like status codes, messages, and contextual information. The folder is organized into multiple files, each responsible for a specific category of errors, such as API-related, database-related, request-related, and service-specific errors. This modular approach promotes code organization and reusability, making it easier to manage and handle errors consistently throughout the application. The `ApiErr` struct implements the `error` interface, allowing it to be used seamlessly with Go's built-in error handling mechanisms.

## Files

### `services_infra.go`
**Role:** service implementation | **Lines:** 214

This file defines error constants and constructor functions related to infrastructure services and networking. It includes sentinel errors for networking issues like `ErrDNSResolution`, `ErrTCPTimeout`, and `ErrConnectionReset`, as well as resource exhaustion errors like `ErrOutOfMemory` and `ErrDiskSpaceFull`. It also defines errors related to timeouts and cancellations, such as `ErrContextDeadline` and `ErrRequestTimeout`, and deployment/runtime platform errors like `ErrBadRollout` and `ErrContainerImage`. The file provides constructor functions like `NewDNSError` to create `ApiErr` instances with specific details for infrastructure-related errors. This file depends on `api.go` as it uses the `ApiErr` struct.

**Key Exports:**
- `NewDNSError`
- `IsTCPTimeoutError`
- `IsTLSHandshakeError`
- `IsConnectionResetError`
- `IsOutOfMemoryError`
- `IsCPUExhaustedError`
- `IsContextDeadlineError`
- `IsClientDisconnectedError`
- `IsComputationTimeoutError`
- `IsBadRolloutError`

---

### `services_llm.go`
**Role:** service implementation | **Lines:** 100

This file defines error constants and constructor functions specific to interacting with Large Language Models (LLMs) and third-party APIs. It includes sentinel errors for issues like `ErrRateLimitExceeded`, `ErrModelOverloaded`, `ErrContextLengthExceeded`, and `ErrContentPolicyViolation`. The file provides constructor functions such as `NewRateLimitError`, `NewModelOverloadedError`, and `NewContextLengthError` to create `ApiErr` instances with specific details relevant to LLM service errors. These constructors allow for setting appropriate status codes and providing informative details about the error, such as the service that exceeded the rate limit or the maximum context length. This file depends on `api.go` as it uses the `ApiErr` struct.

**Key Exports:**
- `NewRateLimitError`
- `IsModelOverloadedError`
- `IsContextLengthError`
- `IsContentPolicyError`
- `IsBillingQuotaError`
- `IsStreamingError`

---

### `services_security.go`
**Role:** service implementation | **Lines:** 158

This file defines error constants and constructor functions related to security, compliance, and service discovery. It includes sentinel errors for dependency and service discovery issues like `ErrServiceUnreachable` and `ErrServiceDiscovery`, as well as security-related errors like `ErrSQLInjection` and `ErrSecretsLeaked`. It also defines errors related to observability and telemetry, such as `ErrTracerExporter` and `ErrLogPipeline`. The file provides constructor functions like `NewServiceUnreachableError` and `NewServiceDiscoveryError` to create `ApiErr` instances with specific details for service-related errors. This file depends on `api.go` as it uses the `ApiErr` struct.

**Key Exports:**
- `NewServiceUnreachableError`
- `IsServiceDiscoveryError`
- `IsSQLInjectionError`
- `IsRequestForgeryError`
- `IsSecretsLeakedError`
- `IsPIIBreachError`
- `IsTracerExporterError`
- `IsLogPipelineError`
- `IsMetricsCardinalityError`

---

### `services_system.go`
**Role:** service implementation | **Lines:** 216

This file defines error constants and constructor functions related to system-level configurations, data consistency, and computational logic. It includes sentinel errors for configuration issues like `ErrConfigMissing` and `ErrConfigInvalid`, data consistency errors like `ErrSchemaVersionMismatch` and `ErrClockSkew`, and computational errors like `ErrDivideByZero` and `ErrNilPointer`. It also defines errors related to serialization and encoding, such as `ErrCircularStructure` and `ErrJSONMarshal`. The file provides constructor functions like `NewConfigError` to create `ApiErr` instances with specific details for configuration-related errors. This file depends on `api.go` as it uses the `ApiErr` struct.

**Key Exports:**
- `NewConfigError`
- `IsEnvironmentVariableError`
- `IsSchemaVersionMismatchError`
- `IsClockSkewError`
- `IsPartialFailureError`
- `IsDivideByZeroError`
- `IsOverflowError`
- `IsNilPointerError`
- `IsCircularStructureError`
- `IsBase64DecodeError`

---

### `api.go`
**Role:** source file | **Lines:** 279

This file defines general API-related error constants and the `ApiErr` struct, which is the core error type used throughout the application. It includes sentinel errors for common HTTP status codes like `ErrForbidden`, `ErrBadRequest`, and `ErrUnauthorized`, as well as errors related to request validation such as `ErrMalformedPayload` and `ErrInvalidField`. The `ApiErr` struct contains fields for the HTTP status code, the underlying error, detailed messages, the field that caused the error (for validation errors), and the underlying cause of the error. It also provides methods for creating new `ApiErr` instances and formatting error messages. This file is foundational, as other files in the folder extend the `ApiErr` struct with more specific error types.

**Key Exports:**
- `NewApiErr`
- `GetFullError`
- `Unwrap`
- `NewNotFoundError`
- `IsBadRequest`
- `IsUnauthorized`
- `IsInternal`
- `IsConflict`
- `IsNotFound`
- `NewBadRequestErrorWithDetails`

---

### `database.go`
**Role:** source file | **Lines:** 258

This file defines error constants and constructor functions specifically related to database operations. It includes sentinel errors for common database issues like `ErrAlreadyExists`, `ErrNotFound`, `ErrDatabaseQuery`, and `ErrDatabaseConnection`, as well as more specific errors like `ErrPoolExhausted` and `ErrUniqueConstraintViolation`. It also provides constructor functions like `NewAlreadyExists` and `NewNotFound` that create `ApiErr` instances with appropriate status codes and messages for common database errors. These functions utilize `fmt.Errorf` to wrap the base database errors with additional context, such as the entity that was not found or already exists. This file depends on `api.go` as it uses the `ApiErr` struct.

**Key Exports:**
- `NewAlreadyExists`
- `NewPoolExhaustedError`
- `IsDeadlockError`
- `IsSerializationFailureError`
- `IsUniqueConstraintViolationError`
- `IsReplicaLagError`
- `IsMigrationMismatchError`
- `IsStorageQuotaFullError`
- `IsTransactionFailedError`
- `IsForeignKeyConstraintError`

---

### `request.go`
**Role:** source file | **Lines:** 171

This file defines error constants and constructor functions related to request processing, authentication, and authorization. It includes sentinel errors for issues like `ErrMissingToken`, `ErrExpiredToken`, and `ErrInsufficientScope`. It also defines errors related to concurrency and synchronization, such as `ErrGoroutineLeak` and `ErrDataRace`. The file provides constructor functions like `NewMissingTokenError` and `NewExpiredTokenError` to create `ApiErr` instances with specific status codes and details for authentication errors. It also defines helper functions like `Malformed` and `BadRequest` for creating common HTTP 400 errors. This file depends on `api.go` as it uses the `ApiErr` struct.

**Key Exports:**
- `Malformed`
- `IsExpiredTokenError`
- `IsInvalidTokenError`
- `IsInsufficientScopeError`
- `IsInsufficientRoleError`
- `IsTokenExpiredError`
- `IsGoroutineLeakError`
- `IsDataRaceError`
- `IsStarvationError`
- `IsPriorityInversionError`

## Stats

- Total files: 7
- Has tests: no
- Has config: no

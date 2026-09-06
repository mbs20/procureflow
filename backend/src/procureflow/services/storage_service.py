import hashlib
import io
import uuid
import zipfile
from pathlib import Path

from procureflow.config import get_settings

settings = get_settings()


class StorageValidationError(ValueError):
    """Raised when uploaded file fails validation."""

    pass


class StorageService:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.storage_local_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(self, filename: str, content: bytes) -> tuple[str, str]:
        """
        Validate file format using extension allowlist, magic bytes, and content checks.
        Returns tuple of (normalized_extension, mime_type).
        """
        # 1. Enforce size limits
        if len(content) == 0:
            raise StorageValidationError("Uploaded file is empty (0 bytes).")
        if len(content) > settings.max_upload_size_bytes:
            max_mb = settings.max_upload_size_bytes // (1024 * 1024)
            raise StorageValidationError(f"File exceeds maximum allowed size of {max_mb} MB.")

        # 2. Check extension
        ext = Path(filename).suffix.lower()
        if not ext:
            raise StorageValidationError(
                "Filename has no extension. Allowed formats: .pdf, .xlsx, .csv."
            )

        # 3. Detect legacy .xls OLE compound document magic bytes
        if content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" or ext == ".xls":
            raise StorageValidationError(
                "Legacy Excel (.xls) format is not supported for v0.1. "
                "Please save or convert your workbook to modern Excel (.xlsx) before uploading."
            )

        # 4. Validate PDF
        if ext == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise StorageValidationError(
                    "File extension is .pdf, but header does not match valid PDF magic bytes (%PDF-)."
                )
            return ".pdf", "application/pdf"

        # 5. Validate XLSX
        elif ext == ".xlsx":
            if not content.startswith(b"PK\x03\x04"):
                raise StorageValidationError(
                    "File extension is .xlsx, but header does not match ZIP archive signature."
                )
            try:
                with zipfile.ZipFile(io.BytesIO(content)) as zf:
                    namelist = zf.namelist()
                    if "[Content_Types].xml" not in namelist and not any(
                        n.startswith("xl/") for n in namelist
                    ):
                        raise StorageValidationError(
                            "File is a valid ZIP archive but does not contain Excel OpenXML structures."
                        )
            except zipfile.BadZipFile as e:
                raise StorageValidationError(
                    f"Invalid or corrupted Excel (.xlsx) archive: {e}"
                ) from e
            return ".xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        # 6. Validate CSV (extension allowlist, text/binary check, encoding, delimiter/header sanity)
        elif ext == ".csv":
            # Binary check: CSV must not contain null bytes
            if b"\x00" in content:
                raise StorageValidationError(
                    "CSV file contains binary/null bytes and is not valid text."
                )

            # Text encoding check
            decoded_text: str | None = None
            for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    decoded_text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if decoded_text is None:
                raise StorageValidationError(
                    "CSV file cannot be decoded as valid UTF-8, ASCII, or Latin-1 text."
                )

            # Delimiter / header sanity check via csv parser
            try:
                import csv

                sample = decoded_text[:4096]
                lines = sample.splitlines()
                if not lines or not any(line.strip() for line in lines):
                    raise StorageValidationError("CSV file is empty or contains only whitespace.")
                reader = csv.reader(io.StringIO(sample))
                rows = [r for r in reader if r]
                if not rows:
                    raise StorageValidationError("CSV file does not contain valid tabular rows.")
            except Exception as e:
                if isinstance(e, StorageValidationError):
                    raise
                raise StorageValidationError(f"Invalid CSV structure: {e}") from e

            return ".csv", "text/csv"

        else:
            raise StorageValidationError(
                f"Unsupported file format '{ext}'. Allowed formats: .pdf, .xlsx, .csv."
            )

    def save_document(
        self, quotation_id: str, filename: str, content: bytes
    ) -> tuple[str, str, str, int]:
        """
        Validates, hashes, and immutably stores a document.
        Returns: (storage_path, file_hash_sha256, mime_type, size_bytes)
        """
        # Validate file content & magic bytes
        normalized_ext, mime_type = self.validate_file(filename, content)

        # Compute SHA-256 hash
        file_hash = hashlib.sha256(content).hexdigest()
        size_bytes = len(content)

        # Generate safe server-side UUID storage path
        # Directory: <base_dir>/quotations/<quotation_id>/
        safe_quotation_id = str(uuid.UUID(quotation_id))  # Validate UUID format
        quotation_dir = (self.base_dir / "quotations" / safe_quotation_id).resolve()

        # Guard against path traversal
        if not str(quotation_dir).startswith(str(self.base_dir)):
            raise StorageValidationError("Path traversal attempt detected in storage destination.")

        quotation_dir.mkdir(parents=True, exist_ok=True)

        doc_uuid = str(uuid.uuid4())
        file_path = quotation_dir / f"{doc_uuid}{normalized_ext}"

        # Write immutable file
        with open(file_path, "wb") as f:
            f.write(content)

        # Return relative storage path or absolute path as string
        storage_rel_path = str(file_path.relative_to(self.base_dir))
        return storage_rel_path, file_hash, mime_type, size_bytes

    def get_absolute_path(self, storage_path: str) -> Path:
        """Resolve a storage path to a validated absolute path."""
        target = (self.base_dir / storage_path).resolve()
        if not str(target).startswith(str(self.base_dir)):
            raise StorageValidationError("Illegal path access outside storage directory.")
        if not target.exists():
            raise FileNotFoundError(f"Stored document not found at: {storage_path}")
        return target


# Global default instance
storage_service = StorageService()

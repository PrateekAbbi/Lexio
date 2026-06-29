export function validatePdfFile(file) {
  if (!file) return "Select a PDF file.";
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    return "Only PDF files are supported.";
  }
  return "";
}

export function normalizeUploadedDocument(data, fallbackFilename) {
  return {
    ...data,
    filename: data.filename || fallbackFilename,
  };
}

/** Countries offered for Faker name generation during ingest (default India). */
export const INGEST_COUNTRIES = [
  "India",
  "United States",
  "United Kingdom",
  "Australia",
  "Canada",
  "Germany",
  "France",
  "Japan",
  "Brazil",
  "Spain",
  "Mexico",
  "Italy",
  "Netherlands",
  "Singapore",
  "Indonesia",
  "Philippines",
  "Malaysia",
  "Thailand",
  "Vietnam",
  "Cambodia",
  "Myanmar",
  "Laos",
  "Brunei",
  "United Arab Emirates",
] as const;

export type IngestCountry = (typeof INGEST_COUNTRIES)[number];

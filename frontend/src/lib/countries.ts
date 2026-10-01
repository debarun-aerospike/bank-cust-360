/** Countries offered for Faker name generation during ingest (default India). */
export const INGEST_COUNTRIES = [
  "Australia",
  "Brazil",
  "Brunei",
  "Cambodia",
  "Canada",
  "France",
  "Germany",
  "India",
  "Indonesia",
  "Italy",
  "Japan",
  "Laos",
  "Malaysia",
  "Mexico",
  "Myanmar",
  "Netherlands",
  "Philippines",
  "Singapore",
  "Spain",
  "Thailand",
  "United Arab Emirates",
  "United Kingdom",
  "United States",
  "Vietnam",
] as const;

export type IngestCountry = (typeof INGEST_COUNTRIES)[number];

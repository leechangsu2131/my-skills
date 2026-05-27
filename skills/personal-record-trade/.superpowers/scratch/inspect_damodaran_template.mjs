import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/Downloads/fcffsimpleginzu.xlsx";
const outputDir = "C:/Users/lee21/.gemini/antigravity/scratch/my-skills/skills/personal-record-trade/.superpowers/scratch";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const summary = await workbook.inspect({
  kind: "workbook,sheet,table,definedName",
  maxChars: 12000,
  tableMaxRows: 8,
  tableMaxCols: 10,
  tableMaxCellChars: 80,
});

const sheets = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 5000,
});

const formulas = await workbook.inspect({
  kind: "formula",
  options: { maxResults: 120 },
  maxChars: 16000,
});

const matches = {};
for (const term of [
  "Revenue",
  "Operating Margin",
  "EBIT",
  "Tax",
  "Reinvestment",
  "FCFF",
  "WACC",
  "Cost of Capital",
  "Terminal",
  "ROIC",
  "Sales to Capital",
  "Value of operating assets",
  "Equity Value",
]) {
  matches[term] = (await workbook.inspect({
    kind: "match",
    searchTerm: term,
    options: { maxResults: 30, matchCase: false },
    maxChars: 6000,
  })).ndjson;
}

await fs.writeFile(`${outputDir}/damodaran_summary.ndjson`, summary.ndjson, "utf8");
await fs.writeFile(`${outputDir}/damodaran_sheets.ndjson`, sheets.ndjson, "utf8");
await fs.writeFile(`${outputDir}/damodaran_formulas.ndjson`, formulas.ndjson, "utf8");
await fs.writeFile(`${outputDir}/damodaran_matches.json`, JSON.stringify(matches, null, 2), "utf8");

console.log("SHEETS");
console.log(sheets.ndjson);
console.log("SUMMARY");
console.log(summary.ndjson.slice(0, 6000));
console.log("FORMULAS");
console.log(formulas.ndjson.slice(0, 6000));

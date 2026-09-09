import type { CompanyProfileData } from "@/types/company";

export function parseKeywordText(...values: Array<string | undefined>) {
  return [...new Set(
    values.flatMap((value) =>
      (value ?? "")
        .split(",")
        .map((keyword) => keyword.trim())
        .filter(Boolean),
    ),
  )];
}

export function getCompanyKeywords(
  profile?: Pick<CompanyProfileData, "required_keywords" | "preferred_keywords">,
) {
  if (!profile) return [];
  return parseKeywordText(profile.required_keywords, profile.preferred_keywords);
}

export function formatCompanyKeywords(
  profile?: Pick<CompanyProfileData, "required_keywords" | "preferred_keywords">,
) {
  return getCompanyKeywords(profile).join(", ");
}

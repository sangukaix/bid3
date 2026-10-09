export type CompanyProfileData = {
  id: number;
  company_name: string;
  business_registration_number: string;
  representative_name: string;
  phone: string;
  email: string;
  website_url_1: string;
  website_url_2: string;
  established_date: string | null;
  address: string;
  industry: string;
  related_industries: string;
  company_type: string;
  employee_count: number | null;
  capital: number | null;
  annual_revenue: number | null;
  main_business: string;
  capabilities: string;
  licenses: string;
  past_performance: string;
  required_keywords: string;
  preferred_keywords: string;
  excluded_keywords: string;
  preferred_bid_type: string;
  preferred_region: string;
  created_at: string;
  updated_at: string;
};

export type CompanyDocumentData = {
  id: number;
  original_name: string;
  document_type: "proposal" | "company_introduction" | "evidence";
  uploaded_at: string;
};

export type CompanyEvidenceItem = {
  id: number; category: string; category_label: string; title: string; content: string;
  source_locations: string[]; evidence_excerpt: string; source_document_id: number | null;
  source_name: string; source_url: string; review_status: "pending" | "approved" | "excluded";
  effective_status: "pending" | "approved" | "excluded" | "expired" | "changed";
  reviewed_by: string; reviewed_at: string | null; valid_until: string | null;
  review_note: string; updated_at: string;
};

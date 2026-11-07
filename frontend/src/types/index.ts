/** Free-form information supplied to the role recommendation assistant. */
export interface UserProfile {
  experiences: string;
  skills: string[];
  personality: string[];
}

/** A local example of a role to explore. */
export interface RecommendedJob {
  id: string;
  title: string;
  reason: string;
  focus: string[];
  gaps: string[];
}

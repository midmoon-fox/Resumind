// Generated from the implemented backend OpenAPI. Do not hand edit.
export interface Schemas {
  AffectedCounts: {
    versions: number;
    exports: number;
    preparations: number;
    preparationExports: number;
    workspaces: number;
    experiences: number;
    tasks: number;
  };
  AnswerRequest: { baseRevision: number; turnId: string; answer: string };
  AsyncAccepted: {
    taskId: string;
    resourceType: Schemas['ResourceType'];
    resourceId: string;
    status: string;
    statusUrl: string;
    resourceUrl: string;
  };
  AsyncAcceptedResponse: { data: Schemas['AsyncAccepted']; requestId: string };
  Body_upload_file_api_files_post: { purpose: 'MATERIAL' | 'JD' | 'AVATAR'; file: string };
  BreakNode: { type: 'hardBreak' };
  'BulletNode-Input': { type: 'bulletList'; content: Array<Schemas['ListItemNode-Input']> };
  'BulletNode-Output': { type: 'bulletList'; content: Array<Schemas['ListItemNode-Output']> };
  Candidate: {
    candidateId: string;
    type: 'PROJECT' | 'INTERNSHIP' | 'CAMPUS' | 'AWARD';
    experienceId: string | null;
    baseExperienceRevision: number | null;
    proposedData: Schemas['app__modules__ai__experience_schemas__ExperienceData'];
    provenance: Array<Schemas['Provenance']>;
    conflicts: Array<string>;
  };
  ColorAttrs: { color: '#333333' | '#1F2937' | '#2563EB' };
  ColorMark: { type: 'textStyle'; attrs: Schemas['ColorAttrs'] };
  CompleteRequest: { baseRevision: number; reason?: string };
  ConfirmRequest: { baseRevision: number; turnId: string; updates: Array<Schemas['Confirmation']> };
  Confirmation: {
    candidateId: string;
    experienceId: string | null;
    baseExperienceRevision: number | null;
    data: Schemas['app__modules__ai__experience_schemas__ExperienceData'];
  };
  CopyResume: { versionId?: string | null; title?: string | null };
  CreateFollowup: {
    workspaceId: string;
    baseWorkspaceRevision: number;
    experienceIds: Array<string>;
    maxRounds?: number;
  };
  CreateResume: {
    workspaceId?: string | null;
    baseWorkspaceRevision?: number | null;
    title: string;
    templateId: string;
    templateVersion: string;
    document: Schemas['Document-Input'];
    style: Schemas['Style'];
  };
  DeletionImpact: {
    resourceType: 'RESUME';
    resourceId: string;
    revision: number;
    affectedCounts: Schemas['AffectedCounts'];
    messages: Array<string>;
  };
  'Document-Input': {
    schemaVersion: '1.0.0';
    profile: Schemas['resume_b__schemas__Profile'];
    sections: Array<Schemas['Section-Input']>;
  };
  'Document-Output': {
    schemaVersion: '1.0.0';
    profile: Schemas['resume_b__schemas__Profile'];
    sections: Array<Schemas['Section-Output']>;
  };
  Download: { url: string; expiresAt: string; fileName: string };
  DownloadOut: { url: string; expiresAt: string; fileName: string };
  Envelope_AsyncAccepted_: { data: Schemas['AsyncAccepted']; requestId: string };
  Envelope_DeletionImpact_: { data: Schemas['DeletionImpact']; requestId: string };
  Envelope_DownloadOut_: { data: Schemas['DownloadOut']; requestId: string };
  Envelope_Download_: { data: Schemas['Download']; requestId: string };
  Envelope_ExperienceOut_: { data: Schemas['ExperienceOut']; requestId: string };
  Envelope_ExportOutput_: { data: Schemas['ExportOutput']; requestId: string };
  Envelope_FileOut_: { data: Schemas['FileOut']; requestId: string };
  Envelope_FollowupView_: { data: Schemas['FollowupView']; requestId: string };
  Envelope_Impact_: { data: Schemas['Impact']; requestId: string };
  Envelope_JdOut_: { data: Schemas['JdOut']; requestId: string };
  Envelope_JdVersionOut_: { data: Schemas['JdVersionOut']; requestId: string };
  Envelope_LoginOut_: { data: Schemas['LoginOut']; requestId: string };
  Envelope_MaterialOut_: { data: Schemas['MaterialOut']; requestId: string };
  Envelope_Page_ExperienceOut__: { data: Schemas['Page_ExperienceOut_']; requestId: string };
  Envelope_Page_JdOut__: { data: Schemas['Page_JdOut_']; requestId: string };
  Envelope_Page_JdVersionOut__: { data: Schemas['Page_JdVersionOut_']; requestId: string };
  Envelope_Page_MaterialOut__: { data: Schemas['Page_MaterialOut_']; requestId: string };
  Envelope_Page_PreparationOutput__: {
    data: Schemas['Page_PreparationOutput_'];
    requestId: string;
  };
  Envelope_Page_ResumeOutput__: { data: Schemas['Page_ResumeOutput_']; requestId: string };
  Envelope_Page_SegmentOut__: { data: Schemas['Page_SegmentOut_']; requestId: string };
  Envelope_Page_VersionOutput__: { data: Schemas['Page_VersionOutput_']; requestId: string };
  Envelope_Page_WorkspaceOut__: { data: Schemas['Page_WorkspaceOut_']; requestId: string };
  Envelope_PreflightOutput_: { data: Schemas['PreflightOutput']; requestId: string };
  Envelope_PreparationExportOutput_: {
    data: Schemas['PreparationExportOutput'];
    requestId: string;
  };
  Envelope_PreparationOutput_: { data: Schemas['PreparationOutput']; requestId: string };
  Envelope_RunView_: { data: Schemas['RunView']; requestId: string };
  Envelope_SuggestionView_Union_RichNode__SuggestionSectionContent__SuggestionEducationContent__SuggestionSkillsContent___: {
    data: Schemas['SuggestionView_Union_RichNode__SuggestionSectionContent__SuggestionEducationContent__SuggestionSkillsContent__'];
    requestId: string;
  };
  Envelope_TemplateList_: { data: Schemas['TemplateList']; requestId: string };
  Envelope_UserOut_: { data: Schemas['UserOut']; requestId: string };
  Envelope_VersionOutput_: { data: Schemas['VersionOutput']; requestId: string };
  Envelope_WorkspaceOut_: { data: Schemas['WorkspaceOut']; requestId: string };
  ErrorBody: { code: string; message: string; details: { [key: string]: unknown } };
  ErrorDetail: { code: string; message: string; details: { [key: string]: unknown } };
  ErrorEnvelope: { error: Schemas['ErrorBody']; requestId: string };
  ErrorOutput: { error: Schemas['ErrorPayload']; requestId: string };
  ErrorPayload: { code: string; message: string; details: { [key: string]: unknown } };
  ErrorResponse: { error: Schemas['ErrorDetail']; requestId: string };
  ExperienceCreate: {
    workspaceId: string;
    type: 'PROJECT' | 'INTERNSHIP' | 'CAMPUS' | 'AWARD';
    data: Schemas['app__schemas__ExperienceData'];
  };
  ExperienceMerge: {
    targetExperienceId: string;
    sources: Array<Schemas['SourceRevision']>;
    data: Schemas['app__schemas__ExperienceData'];
    status: 'CANDIDATE' | 'CONFIRMED';
    excluded: boolean;
    sourceMappings: Array<Schemas['SourceMapping']>;
  };
  ExperienceOut: {
    id: string;
    workspaceId: string;
    type: 'PROJECT' | 'INTERNSHIP' | 'CAMPUS' | 'AWARD';
    data: Schemas['app__schemas__ExperienceData'];
    provenance: Array<Schemas['Provenance']>;
    status: 'CANDIDATE' | 'CONFIRMED';
    excluded: boolean;
    revision: number;
    createdAt: string;
    updatedAt: string;
  };
  ExperiencePatch: {
    baseRevision: number;
    type?: 'PROJECT' | 'INTERNSHIP' | 'CAMPUS' | 'AWARD' | null;
    excluded?: boolean | null;
    data?: Schemas['app__schemas__ExperienceData'] | null;
    status?: 'CANDIDATE' | 'CONFIRMED' | null;
  };
  ExperienceRef: { id: string; revision: number };
  ExportOutput: {
    id: string;
    taskId: string;
    resumeVersionId: string;
    format: 'PDF' | 'DOCX' | 'HTML';
    fileName: string;
    status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCEL_REQUESTED' | 'CANCELLED';
    fileId: string | null;
    warnings: Array<string>;
    error: Schemas['resume_b__schemas__TaskError'] | null;
    createdAt: string;
  };
  ExportRequest: {
    resumeId: string;
    baseRevision: number;
    format: 'PDF' | 'DOCX' | 'HTML';
    fileName?: string | null;
  };
  FieldSource: { experienceId: string; jsonPointer: string };
  FileOut: {
    id: string;
    purpose: string;
    originalName: string;
    mimeType: string;
    sizeBytes: number;
    createdAt: string;
  };
  FollowupView: {
    id: string;
    workspaceId: string;
    status:
      | 'GENERATING'
      | 'AWAITING_ANSWER'
      | 'ANALYZING_ANSWER'
      | 'REVIEW_REQUIRED'
      | 'READY_NEXT'
      | 'COMPLETED'
      | 'FAILED';
    revision: number;
    roundsShown: number;
    maxRounds: number;
    pendingTaskId: string | null;
    lastTaskId: string | null;
    error: Schemas['app__modules__tasks__schemas__TaskError'] | null;
    currentTurnId: string | null;
    endedReason: string | null;
    turns: Array<Schemas['TurnView']>;
  };
  GenerateRequest: {
    workspaceId: string;
    baseWorkspaceRevision: number;
    experienceRevisions: Array<Schemas['ExperienceRef']>;
    templateId: 'simple' | 'project';
    templateVersion: '1.0.0';
    sectionTypes: Array<'PROJECTS' | 'INTERNSHIPS' | 'CAMPUS' | 'AWARDS' | 'EDUCATION' | 'SKILLS' | 'ACHIEVEMENTS' | 'CERTIFICATES' | 'GOAL' | 'CHARTS' | 'HOBBIES' | 'PUBLICATIONS' | 'REFERENCES' | 'SOCIAL_LINKS' | 'STRENGTHS' | 'TEXT' | 'VOLUNTEERING' | 'WORK_EXPERIENCE'>;
    title?: string;
  };
  Impact: {
    resourceType: string;
    resourceId: string;
    revision: number | null;
    affectedCounts: { [key: string]: number };
    messages: Array<string>;
  };
  'Item-Input': {
    id: string;
    title: string;
    subtitle: string;
    startDate: string | null;
    endDate: string | null;
    isCurrent: boolean;
    description: Schemas['RichNode-Input'];
    experienceId: string | null;
    sourceRevision: number | null;
  };
  'Item-Output': {
    id: string;
    title: string;
    subtitle: string;
    startDate: string | null;
    endDate: string | null;
    isCurrent: boolean;
    description: Schemas['RichNode-Output'];
    experienceId: string | null;
    sourceRevision: number | null;
  };
  ItemTarget: { kind: 'ITEM_DESCRIPTION'; sectionId: string; itemId: string };
  JdConfirm: {
    baseRevision: number;
    jdVersionId: string;
    title: string;
    originalText: string;
    jobTitle: string | null;
    companyName: string | null;
    requirements: Array<Schemas['Requirement-Input']>;
  };
  JdCreate: {
    title?: string | null;
    sourceType?: 'TEXT' | 'IMAGE' | 'URL' | null;
    text?: string | null;
    fileId?: string | null;
    url?: string | null;
  };
  JdOut: {
    id: string;
    title: string;
    currentVersionId: string;
    revision: number;
    createdAt: string;
    updatedAt: string;
  };
  JdPatch: { baseRevision: number; title: string };
  JdSnapshot: {
    sourceJdId: string | null;
    sourceJdVersionId: string | null;
    jobTitle: string | null;
    companyName: string | null;
    originalText: string;
    requirements: Array<Schemas['resume_b__schemas__Requirement']>;
  };
  JdVersionCreate: {
    baseRevision: number;
    sourceType?: 'TEXT' | 'IMAGE' | 'URL' | null;
    originalText?: string | null;
    fileId?: string | null;
    url?: string | null;
  };
  JdVersionOut: {
    id: string;
    jdId: string;
    versionNo: number;
    status: string;
    taskId: string;
    sourceType: string;
    originalText: string;
    fileId: string | null;
    sourceUrl: string | null;
    jobTitle: string | null;
    companyName: string | null;
    requirements: Array<Schemas['app__schemas__Requirement']>;
    createdAt: string;
  };
  JobView: {
    id: string;
    title: string;
    company: string;
    city: string;
    salaryText: string | null;
    sourceUrl: string;
    fetchedAt: string;
    publishedAt: string | null;
    availability: 'UNKNOWN' | 'ACTIVE' | 'EXPIRED';
    reasons: Array<string>;
    gaps: Array<string>;
  };
  Kind:
    | 'PARSE_MATERIAL'
    | 'ANALYZE_JD'
    | 'GENERATE_QUESTION'
    | 'ANALYZE_ANSWER'
    | 'GENERATE_RESUME'
    | 'REWRITE_ITEM'
    | 'EXPORT_RESUME'
    | 'GENERATE_PREPARATION'
    | 'EXPORT_PREPARATION'
    | 'RECOMMEND_JOBS';
  LinkAttrs: { href: string };
  LinkMark: { type: 'link'; attrs: Schemas['LinkAttrs'] };
  ListAttrs: { start?: number };
  'ListItemNode-Input': {
    type: 'listItem';
    content: Array<
      Schemas['ParagraphNode'] | Schemas['BulletNode-Input'] | Schemas['OrderedNode-Input']
    >;
  };
  'ListItemNode-Output': {
    type: 'listItem';
    content: Array<
      Schemas['ParagraphNode'] | Schemas['BulletNode-Output'] | Schemas['OrderedNode-Output']
    >;
  };
  Login: { email: string; password: string };
  LoginOut: {
    user: Schemas['UserOut'];
    expiresAt: string;
    accessToken: string;
    tokenType: 'Bearer';
  };
  MaterialCreate: {
    workspaceId: string;
    kind: 'TEXT' | 'FILE' | 'URL' | 'ZIP';
    fileId?: string | null;
    text?: string | null;
    url?: string | null;
    title?: string | null;
  };
  MaterialOut: {
    id: string;
    workspaceId: string;
    kind: string;
    fileId: string | null;
    title: string;
    status: string;
    taskId: string;
    textPreview: string;
    error: Schemas['app__schemas__TaskError'] | null;
    createdAt: string;
  };
  MePatch: { username?: string | null; avatarFileId?: string | null };
  'OrderedNode-Input': {
    type: 'orderedList';
    content: Array<Schemas['ListItemNode-Input']>;
    attrs?: Schemas['ListAttrs'];
  };
  'OrderedNode-Output': {
    type: 'orderedList';
    content: Array<Schemas['ListItemNode-Output']>;
    attrs?: Schemas['ListAttrs'];
  };
  Page_ExperienceOut_: {
    items: Array<Schemas['ExperienceOut']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_JdOut_: { items: Array<Schemas['JdOut']>; page: number; pageSize: number; total: number };
  Page_JdVersionOut_: {
    items: Array<Schemas['JdVersionOut']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_MaterialOut_: {
    items: Array<Schemas['MaterialOut']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_PreparationOutput_: {
    items: Array<Schemas['PreparationOutput']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_ResumeOutput_: {
    items: Array<Schemas['ResumeOutput']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_SegmentOut_: {
    items: Array<Schemas['SegmentOut']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_VersionOutput_: {
    items: Array<Schemas['VersionOutput']>;
    page: number;
    pageSize: number;
    total: number;
  };
  Page_WorkspaceOut_: {
    items: Array<Schemas['WorkspaceOut']>;
    page: number;
    pageSize: number;
    total: number;
  };
  ParagraphNode: { type: 'paragraph'; content?: Array<Schemas['TextNode'] | Schemas['BreakNode']> };
  PatchPreparation: { baseRevision: number; content: Schemas['PreparationContent'] };
  PatchResume: {
    baseRevision: number;
    title?: string | null;
    document?: Schemas['Document-Input'] | null;
    style?: Schemas['Style'] | null;
    templateId?: string | null;
    templateVersion?: string | null;
  };
  Preflight: { baseRevision: number; format: 'PDF' | 'DOCX' | 'HTML' };
  PreflightOutput: { canExport: boolean; issues: Array<Schemas['resume_b__schemas__Issue']> };
  PreparationContent: { introduction: string | null; questions: Array<Schemas['Question']> };
  PreparationExportOutput: {
    id: string;
    taskId: string;
    preparationId: string;
    sourceRevision: number;
    format: 'PDF' | 'DOCX';
    fileName: string;
    status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCEL_REQUESTED' | 'CANCELLED';
    fileId: string | null;
    error: Schemas['resume_b__schemas__TaskError'] | null;
  };
  PreparationExportRequest: {
    baseRevision: number;
    format: 'PDF' | 'DOCX';
    fileName?: string | null;
  };
  PreparationOutput: {
    id: string;
    taskId: string;
    resumeVersionId: string;
    type: 'INTRODUCTION' | 'INTERVIEW_QUESTIONS';
    revision: number;
    status: 'GENERATING' | 'READY' | 'FAILED';
    content: Schemas['PreparationContent'];
    isOutdated: boolean;
    createdAt: string;
    updatedAt: string;
  };
  PreparationRequest: {
    resumeVersionId: string;
    type: 'INTRODUCTION' | 'INTERVIEW_QUESTIONS';
    questionCount?: number;
    tone?: string;
  };
  ProfileTarget: { kind: 'PROFILE_FIELD'; sectionId: string; field: 'education' | 'skills' };
  Provenance: {
    jsonPointer: string;
    segmentIds: Array<string>;
    turnIds: Array<string>;
    origin: 'MATERIAL' | 'USER_INPUT' | 'FOLLOWUP';
  };
  Question: {
    id: string;
    number: number;
    question: string;
    referenceAnswer: string;
    basisItemIds: Array<string>;
    missingFacts: Array<string>;
  };
  RecommendRequest: {
    resumeVersionId: string;
    city: string;
    direction: string;
    experienceLevel: string;
  };
  Registration: { email: string; password: string; username: string };
  'Requirement-Input': {
    id: string;
    category: string;
    text: string;
    necessity: 'REQUIRED' | 'PREFERRED' | 'UNSPECIFIED';
    evidenceQuote: string;
  };
  ResourceRef: { resourceType: Schemas['ResourceType']; resourceId: string; resourceUrl: string };
  ResourceType:
    | 'MATERIAL'
    | 'JD_VERSION'
    | 'FOLLOWUP_SESSION'
    | 'RESUME'
    | 'SUGGESTION'
    | 'EXPORT'
    | 'PREPARATION'
    | 'PREPARATION_EXPORT'
    | 'RECOMMENDATION_RUN';
  Restore: { baseRevision: number; versionId: string };
  ResumeOutput: {
    id: string;
    workspaceId: string | null;
    title: string;
    revision: number;
    generationTaskId: string | null;
    generationStatus: string | null;
    document: Schemas['Document-Output'];
    style: Schemas['Style'];
    templateId: string;
    templateVersion: string;
    jdSnapshot: Schemas['JdSnapshot'] | null;
    createdAt: string;
    updatedAt: string;
  };
  RetryRequest: { expectedAttempt: number };
  RevisionRequest: { baseRevision: number };
  'RichNode-Input': {
    type: 'doc';
    content: Array<
      Schemas['ParagraphNode'] | Schemas['BulletNode-Input'] | Schemas['OrderedNode-Input']
    >;
  };
  'RichNode-Output': {
    type: 'doc';
    content: Array<
      Schemas['ParagraphNode'] | Schemas['BulletNode-Output'] | Schemas['OrderedNode-Output']
    >;
  };
  RunView: {
    id: string;
    taskId: string;
    resumeVersionId: string;
    status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCEL_REQUESTED' | 'CANCELLED';
    filters: { [key: string]: unknown };
    jobs: Array<Schemas['JobView']>;
    error: Schemas['app__modules__tasks__schemas__TaskError'] | null;
  };
  SaveJobRequest: { title?: string };
  'Section-Input': {
    id: string;
    type: 'EDUCATION' | 'PROJECTS' | 'INTERNSHIPS' | 'CAMPUS' | 'AWARDS' | 'SKILLS' | 'ACHIEVEMENTS' | 'CERTIFICATES' | 'GOAL' | 'CHARTS' | 'HOBBIES' | 'PUBLICATIONS' | 'REFERENCES' | 'SOCIAL_LINKS' | 'STRENGTHS' | 'TEXT' | 'VOLUNTEERING' | 'WORK_EXPERIENCE';
    title: string;
    visible: boolean;
    items: Array<Schemas['Item-Input']>;
    chartData?: Array<{ label: string; value: number; unit: string }> | null;
    links?: Array<{ platform: string; label: string; url: string }> | null;
    text?: Schemas['RichNode-Input'] | null;
  };
  'Section-Output': {
    id: string;
    type: 'EDUCATION' | 'PROJECTS' | 'INTERNSHIPS' | 'CAMPUS' | 'AWARDS' | 'SKILLS' | 'ACHIEVEMENTS' | 'CERTIFICATES' | 'GOAL' | 'CHARTS' | 'HOBBIES' | 'PUBLICATIONS' | 'REFERENCES' | 'SOCIAL_LINKS' | 'STRENGTHS' | 'TEXT' | 'VOLUNTEERING' | 'WORK_EXPERIENCE';
    title: string;
    visible: boolean;
    items: Array<Schemas['Item-Output']>;
    chartData?: Array<{ label: string; value: number; unit: string }> | null;
    links?: Array<{ platform: string; label: string; url: string }> | null;
    text?: Schemas['RichNode-Output'] | null;
  };
  SectionTarget: { kind: 'SECTION_CONTENT'; sectionId: string };
  SegmentOut: {
    id: string;
    materialId: string;
    page: number | null;
    ordinal: number;
    text: string;
    extractionMethod: string;
  };
  SimpleMark: { type: 'bold' | 'italic' | 'underline' };
  Snapshot: { baseRevision: number; label?: string | null };
  SourceMapping: { jsonPointer: string; sources: Array<Schemas['FieldSource']> };
  SourceRevision: { id: string; revision: number };
  Status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCEL_REQUESTED' | 'CANCELLED';
  Style: {
    fontFamily: 'Microsoft YaHei' | 'SimSun';
    fontSize: number;
    lineHeight: number;
    accentColor: '#333333' | '#1F2937' | '#2563EB';
    sectionGap: number;
  };
  StylePolicy: {
    fontFamilies: Array<string>;
    colors: Array<string>;
    fontSizeMin: number;
    fontSizeMax: number;
    lineHeightMin: number;
    lineHeightMax: number;
  };
  SuggestRequest: {
    baseRevision: number;
    target: Schemas['ItemTarget'] | Schemas['SectionTarget'] | Schemas['ProfileTarget'];
    instruction: string;
  };
  SuggestionEducationContent: { education: Array<Schemas['resume_b__schemas__Education']> };
  SuggestionItemContent: { itemId: string; description: Schemas['RichNode-Output'] };
  SuggestionSectionContent: { items: Array<Schemas['SuggestionItemContent']> };
  SuggestionSkillsContent: { skills: Array<string> };
  SuggestionView_Union_RichNode__SuggestionSectionContent__SuggestionEducationContent__SuggestionSkillsContent__: {
    id: string;
    taskId: string;
    resumeId: string;
    baseRevision: number;
    target: Schemas['ItemTarget'] | Schemas['SectionTarget'] | Schemas['ProfileTarget'];
    original:
      | Schemas['RichNode-Output']
      | Schemas['SuggestionSectionContent']
      | Schemas['SuggestionEducationContent']
      | Schemas['SuggestionSkillsContent'];
    proposed:
      | Schemas['RichNode-Output']
      | Schemas['SuggestionSectionContent']
      | Schemas['SuggestionEducationContent']
      | Schemas['SuggestionSkillsContent']
      | null;
    explanation: string;
    needsFactConfirmation: boolean;
    status: 'GENERATING' | 'READY' | 'APPLIED' | 'REJECTED' | 'STALE' | 'FAILED';
    appliedRevision: number | null;
    createdAt: string;
  };
  TaskResponse: { data: Schemas['TaskView']; requestId: string };
  TaskView: {
    id: string;
    kind: Schemas['Kind'];
    status: Schemas['Status'];
    stage: string;
    attempt: number;
    result: Schemas['ResourceRef'] | null;
    error: Schemas['app__modules__tasks__schemas__TaskError'] | null;
    createdAt: string;
    updatedAt: string;
  };
  TemplateList: {
    items: Array<Schemas['TemplateOutput']>;
    page: number;
    pageSize: number;
    total: number;
  };
  TemplateOutput: {
    id: string;
    version: string;
    name: string;
    supportedFormats: Array<'PDF' | 'DOCX' | 'HTML'>;
    allowedSectionTypes: Array<string>;
    stylePolicy: Schemas['StylePolicy'];
    previewUrl: string | null;
  };
  TextNode: {
    type: 'text';
    text: string;
    marks?: Array<Schemas['SimpleMark'] | Schemas['LinkMark'] | Schemas['ColorMark']>;
  };
  TurnRequest: { baseRevision: number; turnId: string };
  TurnView: {
    id: string;
    ordinal: number;
    status:
      'AWAITING_ANSWER' | 'ANALYZING' | 'REVIEW_REQUIRED' | 'CONFIRMED' | 'SKIPPED' | 'ABANDONED';
    question: string;
    reason: string;
    experienceId: string | null;
    answer: string | null;
    candidateUpdates: Array<Schemas['Candidate']>;
    createdAt: string;
  };
  UserOut: {
    id: string;
    email: string;
    username: string;
    avatarFileId: string | null;
    createdAt: string;
  };
  VersionOutput: {
    id: string;
    resumeId: string;
    sourceRevision: number;
    label: string;
    document: Schemas['Document-Output'];
    style: Schemas['Style'];
    templateId: string;
    templateVersion: string;
    jdSnapshot: Schemas['JdSnapshot'] | null;
    reason: 'MANUAL' | 'EXPORT' | 'BEFORE_RESTORE';
    createdAt: string;
  };
  WorkspaceCreate: { title?: string; direction?: string | null };
  WorkspaceOut: {
    id: string;
    title: string;
    direction: string | null;
    profile: Schemas['app__schemas__Profile'];
    jdVersionId: string | null;
    activeFollowupSessionId: string | null;
    step: 'JD' | 'PROFILE' | 'MATERIALS' | 'FOLLOWUP' | 'EDITOR';
    revision: number;
    createdAt: string;
    updatedAt: string;
  };
  WorkspacePatch: {
    baseRevision: number;
    title?: string | null;
    direction?: string | null;
    profile?: Schemas['app__schemas__Profile'] | null;
    jdVersionId?: string | null;
    step?: 'JD' | 'PROFILE' | 'MATERIALS' | 'FOLLOWUP' | 'EDITOR' | null;
  };
  app__modules__ai__experience_schemas__ExperienceData: {
    name: string;
    startDate: string | null;
    endDate: string | null;
    isCurrent: boolean;
    background: string;
    personalRole: string;
    actions: Array<string>;
    outcomes: Array<string>;
    technologies: Array<string>;
  };
  app__modules__c_core__views__Envelope_ResumeOutput_: {
    data: Schemas['ResumeOutput'];
    requestId: string;
  };
  app__modules__tasks__schemas__Issue: {
    code: string;
    severity: string;
    path: string;
    message: string;
  };
  app__modules__tasks__schemas__TaskError: {
    code: string;
    message: string;
    canRetry: boolean;
    issues?: Array<Schemas['app__modules__tasks__schemas__Issue']> | null;
  };
  app__schemas__Accepted: {
    taskId: string;
    resourceType: string;
    resourceId: string;
    status: string;
    statusUrl: string;
    resourceUrl: string;
  };
  app__schemas__Education: {
    startDate: string | null;
    endDate: string | null;
    isCurrent: boolean;
    id: string;
    school: string;
    major: string;
    degree: string;
  };
  app__schemas__Envelope_Accepted_: { data: Schemas['app__schemas__Accepted']; requestId: string };
  app__schemas__ExperienceData: {
    startDate: string | null;
    endDate: string | null;
    isCurrent: boolean;
    name: string;
    background: string;
    personalRole: string;
    actions: Array<string>;
    outcomes: Array<string>;
    technologies: Array<string>;
  };
  app__schemas__Profile: {
    photoData?: string | null;
    name: string;
    phone: string | null;
    email: string;
    intention: string;
    age: number | null;
    education: Array<Schemas['app__schemas__Education']>;
    skills: Array<string>;
  };
  app__schemas__Requirement: {
    id: string;
    category: string;
    text: string;
    necessity: 'REQUIRED' | 'PREFERRED' | 'UNSPECIFIED';
    evidenceQuote: string;
  };
  app__schemas__TaskError: { code: string; message: string; canRetry: boolean };
  resume_b__schemas__Accepted: {
    taskId: string;
    resourceType: 'EXPORT' | 'PREPARATION_EXPORT';
    resourceId: string;
    status: 'QUEUED' | 'RUNNING' | 'SUCCEEDED' | 'FAILED' | 'CANCEL_REQUESTED' | 'CANCELLED';
    statusUrl: string;
    resourceUrl: string;
  };
  resume_b__schemas__Education: {
    id: string;
    school: string;
    major: string;
    degree: string;
    startDate: string | null;
    endDate: string | null;
    isCurrent: boolean;
  };
  resume_b__schemas__Envelope_Accepted_: {
    data: Schemas['resume_b__schemas__Accepted'];
    requestId: string;
  };
  resume_b__schemas__Envelope_ResumeOutput_: { data: Schemas['ResumeOutput']; requestId: string };
  resume_b__schemas__Issue: {
    code: string;
    severity: 'ERROR' | 'WARNING';
    path: string;
    message: string;
  };
  resume_b__schemas__Profile: {
    photoData?: string | null;
    name: string;
    phone: string | null;
    email: string;
    intention: string;
    age: number | null;
    education: Array<Schemas['resume_b__schemas__Education']>;
    skills: Array<string>;
  };
  resume_b__schemas__Requirement: {
    id: string;
    category: string;
    text: string;
    necessity: 'REQUIRED' | 'PREFERRED' | 'UNSPECIFIED';
    evidenceQuote: string;
  };
  resume_b__schemas__TaskError: {
    code: string;
    message: string;
    canRetry: boolean;
    issues?: Array<Schemas['resume_b__schemas__Issue']> | null;
  };
}
export type Schema<K extends keyof Schemas> = Schemas[K];

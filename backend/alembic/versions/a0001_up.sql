CREATE TABLE auth_idempotency (
	anonymous_session_hash BINARY(32) NOT NULL, 
	operation_key VARCHAR(200) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	client_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	request_sha256 BINARY(32) NOT NULL, 
	state VARCHAR(24) NOT NULL, 
	http_status SMALLINT UNSIGNED, 
	response_json JSON, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_auth_intent UNIQUE (anonymous_session_hash, operation_key, client_key)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE TABLE users (
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	avatar_file_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	status VARCHAR(20) NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE TABLE audit_events (
	action VARCHAR(100) NOT NULL, 
	resource_type VARCHAR(40) NOT NULL, 
	resource_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	request_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	metadata_json JSON NOT NULL, 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_audit_owner_time ON audit_events (user_id, created_at, id);

CREATE TABLE files (
	purpose VARCHAR(32) NOT NULL, 
	object_key VARCHAR(512) COLLATE utf8mb4_bin NOT NULL, 
	original_name VARCHAR(255) NOT NULL, 
	mime_type VARCHAR(100) NOT NULL, 
	size_bytes BIGINT UNSIGNED NOT NULL, 
	sha256 BINARY(32) NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	deleted_at DATETIME(6), 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (object_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_files_owner_time ON files (user_id, created_at, id);

CREATE TABLE idempotency_records (
	operation_key VARCHAR(200) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	client_key VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	request_sha256 BINARY(32) NOT NULL, 
	state VARCHAR(24) NOT NULL, 
	http_status SMALLINT UNSIGNED, 
	response_json JSON, 
	resource_type VARCHAR(40), 
	resource_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_idempotency_intent UNIQUE (user_id, operation_key, client_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE TABLE job_descriptions (
	title VARCHAR(200) NOT NULL, 
	current_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	revision INTEGER UNSIGNED NOT NULL, 
	deleted_at DATETIME(6), 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_jd_revision CHECK (revision >= 1), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_jd_owner_time ON job_descriptions (user_id, created_at, id);

CREATE TABLE sessions (
	token_hash BINARY(32) NOT NULL, 
	csrf_hash BINARY(32) NOT NULL, 
	expires_at DATETIME(6) NOT NULL, 
	revoked_at DATETIME(6), 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (token_hash), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_sessions_expiry ON sessions (expires_at);

CREATE INDEX ix_sessions_owner_time ON sessions (user_id, created_at);

CREATE TABLE jd_versions (
	jd_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	version_no INTEGER UNSIGNED NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	source_type VARCHAR(24) NOT NULL, 
	original_text MEDIUMTEXT NOT NULL, 
	file_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	source_url VARCHAR(2048), 
	job_title VARCHAR(200), 
	company_name VARCHAR(200), 
	requirements_json JSON NOT NULL, 
	confirmed_at DATETIME(6), 
	purged_at DATETIME(6), 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_jd_version_no UNIQUE (jd_id, version_no), 
	FOREIGN KEY(jd_id) REFERENCES job_descriptions (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE TABLE workspaces (
	title VARCHAR(100) NOT NULL, 
	direction VARCHAR(100), 
	profile_json JSON NOT NULL, 
	jd_version_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	active_followup_session_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	step VARCHAR(24) NOT NULL, 
	revision INTEGER UNSIGNED NOT NULL, 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_workspace_revision CHECK (revision >= 1), 
	FOREIGN KEY(jd_version_id) REFERENCES jd_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_workspace_owner_time ON workspaces (user_id, updated_at, id);

CREATE TABLE experiences (
	workspace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	generation_task_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	candidate_key VARCHAR(100) COLLATE utf8mb4_bin, 
	type VARCHAR(24) NOT NULL, 
	data_json JSON NOT NULL, 
	status VARCHAR(24) NOT NULL, 
	revision INTEGER UNSIGNED NOT NULL, 
	excluded BOOL NOT NULL, 
	merged_into_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	deleted_at DATETIME(6), 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_experience_revision CHECK (revision >= 1), 
	CONSTRAINT ck_experience_not_self CHECK (merged_into_id IS NULL OR merged_into_id <> id), 
	CONSTRAINT uq_experience_candidate UNIQUE (generation_task_id, candidate_key), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(merged_into_id) REFERENCES experiences (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_experience_workspace_status ON experiences (workspace_id, status, id);

CREATE TABLE materials (
	workspace_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	file_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	kind VARCHAR(20) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	input_text MEDIUMTEXT, 
	source_url VARCHAR(2048), 
	status VARCHAR(24) NOT NULL, 
	error_json JSON, 
	deleted_at DATETIME(6), 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(workspace_id) REFERENCES workspaces (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(file_id) REFERENCES files (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_material_owner_time ON materials (user_id, created_at, id);

CREATE INDEX ix_material_workspace_time ON materials (workspace_id, created_at, id);

CREATE TABLE material_segments (
	material_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	ordinal INTEGER UNSIGNED NOT NULL, 
	page_no INTEGER UNSIGNED, 
	text MEDIUMTEXT NOT NULL, 
	extraction_method VARCHAR(32) NOT NULL, 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_segment_ordinal UNIQUE (material_id, ordinal), 
	FOREIGN KEY(material_id) REFERENCES materials (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE TABLE experience_sources (
	experience_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	experience_revision INTEGER UNSIGNED NOT NULL, 
	json_pointer VARCHAR(500) NOT NULL, 
	segment_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	turn_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin, 
	origin VARCHAR(24) NOT NULL, 
	user_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL, 
	created_at DATETIME(6) NOT NULL, 
	updated_at DATETIME(6) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT ck_source_origin CHECK ((origin='MATERIAL' AND segment_id IS NOT NULL AND turn_id IS NULL) OR (origin='FOLLOWUP' AND turn_id IS NOT NULL AND segment_id IS NULL) OR (origin='USER_INPUT' AND segment_id IS NULL AND turn_id IS NULL)), 
	FOREIGN KEY(experience_id) REFERENCES experiences (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(segment_id) REFERENCES material_segments (id) ON DELETE RESTRICT ON UPDATE RESTRICT, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE RESTRICT ON UPDATE RESTRICT
)ENGINE=InnoDB CHARSET=utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE INDEX ix_source_experience_revision ON experience_sources (experience_id, experience_revision);

ALTER TABLE users ADD CONSTRAINT fk_users_avatar FOREIGN KEY(avatar_file_id) REFERENCES files (id) ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE job_descriptions ADD CONSTRAINT fk_jd_current_version FOREIGN KEY(current_version_id) REFERENCES jd_versions (id) ON DELETE RESTRICT ON UPDATE RESTRICT;

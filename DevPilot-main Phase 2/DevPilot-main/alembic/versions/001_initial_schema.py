"""Initial database schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-12-19

Creates initial tables for DevPilot:
- users
- teams
- team_members
- projects
- project_teams
- artifacts
- workflow_runs
- api_keys
- agent_messages
- integration_connections
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_superuser', sa.Boolean(), default=False),
        sa.Column('email_verified', sa.Boolean(), default=False),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_login', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])
    
    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_teams_slug', 'teams', ['slug'])
    
    # Create team_members association table
    op.create_table(
        'team_members',
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(50), default='developer'),
        sa.Column('joined_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('owner_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('status', sa.String(50), default='draft'),
        sa.Column('current_stage', sa.String(50), default='initialization'),
        sa.Column('requirements', sa.JSON(), nullable=True),
        sa.Column('llm_provider', sa.String(50), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('settings', sa.JSON(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_projects_slug', 'projects', ['slug'])
    op.create_index('ix_projects_owner_status', 'projects', ['owner_id', 'status'])
    op.create_unique_constraint('uq_projects_owner_slug', 'projects', ['owner_id', 'slug'])
    
    # Create project_teams association table
    op.create_table(
        'project_teams',
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('team_id', sa.String(36), sa.ForeignKey('teams.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('assigned_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create artifacts table
    op.create_table(
        'artifacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_format', sa.String(50), default='markdown'),
        sa.Column('version', sa.Integer(), default=1),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('artifacts.id'), nullable=True),
        sa.Column('is_approved', sa.Boolean(), default=False),
        sa.Column('approved_by', sa.String(36), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('approved_at', sa.DateTime(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index('ix_artifacts_project_type', 'artifacts', ['project_id', 'artifact_type'])
    
    # Create workflow_runs table
    op.create_table(
        'workflow_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False),
        sa.Column('run_number', sa.Integer(), nullable=False),
        sa.Column('current_stage', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), default='running'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('state', sa.JSON(), default=dict),
        sa.Column('active_agents', sa.JSON(), nullable=True),
        sa.Column('agent_logs', sa.JSON(), nullable=True),
        sa.Column('started_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_workflow_runs_project_status', 'workflow_runs', ['project_id', 'status'])
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False, unique=True),
        sa.Column('key_prefix', sa.String(10), nullable=False),
        sa.Column('scopes', sa.JSON(), default=list),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('usage_count', sa.Integer(), default=0),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    
    # Create agent_messages table
    op.create_table(
        'agent_messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('workflow_run_id', sa.String(36), sa.ForeignKey('workflow_runs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(100), nullable=False),
        sa.Column('agent_type', sa.String(50), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('correlation_id', sa.String(36), nullable=True),
        sa.Column('reply_to', sa.String(36), sa.ForeignKey('agent_messages.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
    )
    op.create_index('ix_agent_messages_workflow_agent', 'agent_messages', ['workflow_run_id', 'agent_id'])
    op.create_index('ix_agent_messages_correlation', 'agent_messages', ['correlation_id'])
    
    # Create integration_connections table
    op.create_table(
        'integration_connections',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('integration_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('is_connected', sa.Boolean(), default=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_integration_connections_user_type', 'integration_connections', ['user_id', 'integration_type'])


def downgrade() -> None:
    op.drop_table('integration_connections')
    op.drop_table('agent_messages')
    op.drop_table('api_keys')
    op.drop_table('workflow_runs')
    op.drop_table('artifacts')
    op.drop_table('project_teams')
    op.drop_table('projects')
    op.drop_table('team_members')
    op.drop_table('teams')
    op.drop_table('users')

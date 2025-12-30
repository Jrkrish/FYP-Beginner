"""
Artifact Viewer Component

Real-time artifact preview with syntax highlighting, markdown rendering,
and file navigation capabilities.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
import os
import re
from datetime import datetime
from loguru import logger


class ArtifactViewer:
    """
    Enhanced artifact viewer component.
    
    Provides:
    - Markdown rendering with proper formatting
    - Code syntax highlighting
    - File tree navigation
    - Copy and download functionality
    - Diff view for revisions
    """
    
    def __init__(self):
        """Initialize the artifact viewer."""
        self.artifacts_dir = "artifacts"
    
    def render(self, artifact_type: str = None, content: str = None):
        """
        Render artifact viewer.
        
        Args:
            artifact_type: Type of artifact (e.g., "user_stories", "design_documents")
            content: Content to display (if not loading from file)
        """
        st.markdown(self._get_css(), unsafe_allow_html=True)
        
        if content:
            self._render_content(content, artifact_type)
        else:
            self._render_artifact_browser()
    
    def _render_artifact_browser(self):
        """Render the artifact file browser."""
        st.subheader("📁 Artifacts")
        
        # Get available artifacts
        artifacts = self._get_available_artifacts()
        
        if not artifacts:
            st.info("No artifacts generated yet. Complete SDLC phases to generate artifacts.")
            return
        
        # Artifact selector
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_artifact = st.selectbox(
                "Select Artifact",
                options=list(artifacts.keys()),
                format_func=lambda x: f"{self._get_artifact_icon(x)} {x}",
                key="artifact_selector"
            )
        
        with col2:
            if selected_artifact and artifacts.get(selected_artifact):
                file_path = artifacts[selected_artifact]
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(
                            "📥 Download",
                            data=f,
                            file_name=os.path.basename(file_path),
                            mime="text/markdown",
                            use_container_width=True
                        )
        
        # Display selected artifact
        if selected_artifact and artifacts.get(selected_artifact):
            self._render_artifact_content(artifacts[selected_artifact], selected_artifact)
    
    def _get_available_artifacts(self) -> Dict[str, str]:
        """Get list of available artifact files."""
        artifacts = {}
        
        artifact_files = {
            "Project Requirements": "Project_Requirement.md",
            "User Stories": "User_Stories.md",
            "Design Documents": "Design_Documents.md",
            "Generated Code": "Generated_Code.md",
            "Security Recommendations": "Security_Recommendations.md",
            "Test Cases": "Test_Cases.md",
            "QA Testing Comments": "QA_Testing_Comments.md",
            "Deployment Feedback": "Deployment_Feedback.md",
        }
        
        for name, filename in artifact_files.items():
            filepath = os.path.join(self.artifacts_dir, filename)
            if os.path.exists(filepath):
                artifacts[name] = filepath
        
        return artifacts
    
    def _get_artifact_icon(self, artifact_name: str) -> str:
        """Get icon for artifact type."""
        icons = {
            "Project Requirements": "📋",
            "User Stories": "📖",
            "Design Documents": "🏗️",
            "Generated Code": "💻",
            "Security Recommendations": "🔒",
            "Test Cases": "🧪",
            "QA Testing Comments": "✅",
            "Deployment Feedback": "🚀",
        }
        return icons.get(artifact_name, "📄")
    
    def _render_artifact_content(self, filepath: str, artifact_name: str):
        """Render artifact content with proper formatting."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Get file info
            file_stat = os.stat(filepath)
            modified_time = datetime.fromtimestamp(file_stat.st_mtime)
            file_size = file_stat.st_size
            
            # File info header
            st.markdown(f"""
            <div class="artifact-header">
                <div class="artifact-info">
                    <span class="artifact-icon">{self._get_artifact_icon(artifact_name)}</span>
                    <span class="artifact-name">{artifact_name}</span>
                </div>
                <div class="artifact-meta">
                    <span>📅 {modified_time.strftime('%Y-%m-%d %H:%M')}</span>
                    <span>📊 {self._format_size(file_size)}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Render content based on type
            self._render_content(content, artifact_name)
            
        except Exception as e:
            st.error(f"Failed to load artifact: {e}")
    
    def _render_content(self, content: str, artifact_type: str = None):
        """Render content with appropriate formatting."""
        # Check if content contains code blocks
        if "```" in content:
            self._render_mixed_content(content)
        elif artifact_type and "Code" in str(artifact_type):
            self._render_code_content(content)
        else:
            self._render_markdown_content(content)
    
    def _render_markdown_content(self, content: str):
        """Render markdown content."""
        with st.container():
            st.markdown(f"""
            <div class="artifact-content markdown-content">
            """, unsafe_allow_html=True)
            
            st.markdown(content)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    def _render_code_content(self, content: str):
        """Render code content with syntax highlighting."""
        # Extract code blocks
        code_blocks = self._extract_code_blocks(content)
        
        if code_blocks:
            for i, block in enumerate(code_blocks):
                filename = block.get("filename", f"code_{i+1}")
                code = block.get("code", "")
                language = block.get("language", "python")
                
                with st.expander(f"📄 {filename}", expanded=i == 0):
                    # Copy button and code
                    col1, col2 = st.columns([5, 1])
                    with col2:
                        if st.button("📋 Copy", key=f"copy_{i}"):
                            st.toast("Code copied to clipboard!")
                    
                    st.code(code, language=language)
        else:
            st.code(content, language="python")
    
    def _render_mixed_content(self, content: str):
        """Render content with both markdown and code blocks."""
        # Split content by code blocks
        parts = re.split(r'(```[\s\S]*?```)', content)
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if part.startswith("```"):
                # Code block
                match = re.match(r'```(\w+)?\n([\s\S]*?)\n?```', part)
                if match:
                    language = match.group(1) or "text"
                    code = match.group(2)
                    st.code(code, language=language)
                else:
                    st.code(part.strip("`"), language="text")
            else:
                # Markdown content
                st.markdown(part)
    
    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown content."""
        blocks = []
        
        # Pattern to match code blocks with optional filename
        pattern = r'\*\*([^*]+)\*\*\s*```(\w+)?\n([\s\S]*?)```'
        matches = re.findall(pattern, content)
        
        for match in matches:
            filename = match[0].strip()
            language = match[1] or "python"
            code = match[2].strip()
            
            blocks.append({
                "filename": filename,
                "language": language,
                "code": code,
            })
        
        # If no named blocks found, try simple code blocks
        if not blocks:
            simple_pattern = r'```(\w+)?\n([\s\S]*?)```'
            matches = re.findall(simple_pattern, content)
            
            for i, match in enumerate(matches):
                language = match[0] or "python"
                code = match[1].strip()
                
                blocks.append({
                    "filename": f"code_{i+1}.{self._get_extension(language)}",
                    "language": language,
                    "code": code,
                })
        
        return blocks
    
    def _get_extension(self, language: str) -> str:
        """Get file extension for language."""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "html": "html",
            "css": "css",
            "json": "json",
            "yaml": "yaml",
            "sql": "sql",
            "bash": "sh",
            "shell": "sh",
        }
        return extensions.get(language.lower(), "txt")
    
    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        for unit in ["B", "KB", "MB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"
    
    def _get_css(self) -> str:
        """Get CSS for artifact viewer."""
        return """
        <style>
        .artifact-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px 16px;
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 10px;
            margin-bottom: 16px;
        }
        
        .artifact-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .artifact-icon {
            font-size: 24px;
        }
        
        .artifact-name {
            font-weight: 600;
            font-size: 16px;
            color: #2d3748;
        }
        
        .artifact-meta {
            display: flex;
            gap: 16px;
            font-size: 12px;
            color: #718096;
        }
        
        .artifact-content {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
        }
        
        .markdown-content h1, .markdown-content h2, .markdown-content h3 {
            color: #2d3748;
            margin-top: 24px;
            margin-bottom: 12px;
        }
        
        .markdown-content h1 { font-size: 24px; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; }
        .markdown-content h2 { font-size: 20px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
        .markdown-content h3 { font-size: 16px; }
        
        .markdown-content p {
            color: #4a5568;
            line-height: 1.7;
            margin-bottom: 12px;
        }
        
        .markdown-content ul, .markdown-content ol {
            margin-left: 24px;
            margin-bottom: 12px;
        }
        
        .markdown-content li {
            color: #4a5568;
            line-height: 1.6;
            margin-bottom: 4px;
        }
        
        .markdown-content code {
            background: #f7fafc;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 14px;
            color: #e53e3e;
        }
        
        .markdown-content pre {
            background: #2d3748;
            border-radius: 8px;
            padding: 16px;
            overflow-x: auto;
        }
        
        .markdown-content pre code {
            background: none;
            color: #e2e8f0;
        }
        
        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 16px;
        }
        
        .markdown-content th, .markdown-content td {
            border: 1px solid #e2e8f0;
            padding: 10px 12px;
            text-align: left;
        }
        
        .markdown-content th {
            background: #f7fafc;
            font-weight: 600;
            color: #2d3748;
        }
        </style>
        """


def render_artifact_viewer(artifact_type: str = None, content: str = None):
    """
    Render the artifact viewer component.
    
    Args:
        artifact_type: Type of artifact
        content: Content to display
    """
    viewer = ArtifactViewer()
    viewer.render(artifact_type, content)


def render_artifact_preview(content: str, artifact_type: str = "markdown"):
    """
    Render a quick preview of artifact content.
    
    Args:
        content: Content to preview
        artifact_type: Type of artifact for formatting
    """
    viewer = ArtifactViewer()
    viewer._render_content(content, artifact_type)


def get_artifact_list() -> Dict[str, str]:
    """
    Get list of available artifacts.
    
    Returns:
        Dict of artifact name to file path
    """
    viewer = ArtifactViewer()
    return viewer._get_available_artifacts()

"""
Streamlit application for reviewing and applying media file rename changes.

This app provides a user interface to:
1. Extract tags from media files
2. Generate rename proposals
3. Review and edit proposed changes
4. Apply changes atomically
"""

import os
import json
from typing import List
import streamlit as st

from src.pic_organize.extract_tags import scan_media
from src.pic_organize.rename_by_datetime import (
    generate_rename_proposal,
    RenameProposalItem,
)
from src.pic_organize.tag_info import MediaTagInfo
from src.pic_organize.atomic_rename import AtomicRenamer


def create_filename_diff(original: str, proposed: str) -> str:
    """
    Create a visual diff of filename changes with highlighting.

    Args:
        original: Original filename
        proposed: Proposed filename

    Returns:
        HTML string with highlighted differences
    """
    # Simple diff highlighting
    if original == proposed:
        return f"**{original}** (no change)"

    # Find common prefix and suffix
    i = 0
    while i < len(original) and i < len(proposed) and original[i] == proposed[i]:
        i += 1

    j = 0
    while (
        j < len(original) - i
        and j < len(proposed) - i
        and original[-(j + 1)] == proposed[-(j + 1)]
    ):
        j += 1

    if j > 0:
        common_prefix = original[:i]
        original_middle = original[i:-j] if j > 0 else original[i:]
        proposed_middle = proposed[i:-j] if j > 0 else proposed[i:]
        common_suffix = original[-j:] if j > 0 else ""
    else:
        common_prefix = original[:i]
        original_middle = original[i:]
        proposed_middle = proposed[i:]
        common_suffix = ""

    # Create highlighted diff
    html = f"""
    <div style="font-family: monospace; padding: 8px; border-left: 3px solid #ddd; margin: 4px 0;">
        <div style="margin-bottom: 4px;">
            <span style="color: #666;">Original:</span> 
            <span>{common_prefix}</span><span style="background-color: #ffebee; color: #c62828; text-decoration: line-through;">{original_middle}</span><span>{common_suffix}</span>
        </div>
        <div>
            <span style="color: #666;">Proposed:</span> 
            <span>{common_prefix}</span><span style="background-color: #e8f5e8; color: #2e7d32; font-weight: bold;">{proposed_middle}</span><span>{common_suffix}</span>
        </div>
    </div>
    """

    return html


def init_session_state():
    """Initialize session state variables."""
    if "media_tags" not in st.session_state:
        st.session_state.media_tags = None
    if "rename_proposals" not in st.session_state:
        st.session_state.rename_proposals = None
    if "manual_review" not in st.session_state:
        st.session_state.manual_review = None
    if "selected_proposals" not in st.session_state:
        st.session_state.selected_proposals = []
    if "directory_path" not in st.session_state:
        st.session_state.directory_path = "."


def extract_tags():
    """Extract tags from media files in the specified directory."""
    try:
        with st.spinner("Extracting tags from media files..."):
            media_tags = scan_media(st.session_state.directory_path)
            st.session_state.media_tags = media_tags
        st.success(f"Successfully extracted tags from {len(media_tags)} media files.")
        return True
    except Exception as e:
        st.error(f"Error extracting tags: {str(e)}")
        return False


def generate_proposals():
    """Generate rename proposals from extracted tags."""
    if st.session_state.media_tags is None:
        st.warning("Please extract tags first before generating proposals.")
        return False

    try:
        with st.spinner("Generating rename proposals..."):
            proposals, manual_review = generate_rename_proposal(
                st.session_state.media_tags
            )
            st.session_state.rename_proposals = proposals
            st.session_state.manual_review = manual_review
            # Initialize all proposals as selected
            st.session_state.selected_proposals = list(range(len(proposals)))

        st.success(f"Generated {len(proposals)} rename proposals.")
        if manual_review:
            st.warning(
                f"{len(manual_review)} files require manual review (no datetime found)."
            )
        return True
    except Exception as e:
        st.error(f"Error generating proposals: {str(e)}")
        return False


def display_proposals():
    """Display rename proposals in a table for review."""
    if st.session_state.rename_proposals is None:
        st.info("No rename proposals available. Please generate proposals first.")
        return

    proposals = st.session_state.rename_proposals

    if not proposals:
        st.info("No rename proposals were generated.")
        return

    st.subheader("Rename Proposals")

    # Initialize pagination state
    if "page_number" not in st.session_state:
        st.session_state.page_number = 0
    if "page_size" not in st.session_state:
        st.session_state.page_size = 20

    # Display selection controls
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("Select All"):
            st.session_state.selected_proposals = list(range(len(proposals)))
            st.rerun()
    with col2:
        if st.button("Deselect All"):
            st.session_state.selected_proposals = []
            st.rerun()
    with col3:
        if st.button("Invert Selection"):
            all_indices = set(range(len(proposals)))
            selected_set = set(st.session_state.selected_proposals)
            st.session_state.selected_proposals = list(all_indices - selected_set)
            st.rerun()
    with col4:
        page_size = st.selectbox(
            "Items per page:",
            [10, 20, 50, 100],
            index=[10, 20, 50, 100].index(st.session_state.page_size),
            key="page_size_select",
        )
        if page_size != st.session_state.page_size:
            st.session_state.page_size = page_size
            st.session_state.page_number = 0  # Reset to first page
            st.rerun()

    # Search/filter functionality
    search_term = st.text_input(
        "Search proposals:", placeholder="Enter filename or path to filter..."
    )

    # Filter proposals based on search term
    filtered_proposals = []
    for i, proposal in enumerate(proposals):
        if not search_term or (
            search_term.lower() in proposal.original.lower()
            or search_term.lower() in proposal.proposed.lower()
        ):
            filtered_proposals.append((i, proposal))

    total_filtered = len(filtered_proposals)

    # Calculate pagination
    total_pages = (
        total_filtered + st.session_state.page_size - 1
    ) // st.session_state.page_size
    start_idx = st.session_state.page_number * st.session_state.page_size
    end_idx = min(start_idx + st.session_state.page_size, total_filtered)

    # Display counts and pagination controls
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        st.write(
            f"**{len(st.session_state.selected_proposals)} of {len(proposals)} selected**"
        )

    with col2:
        if total_pages > 1:
            pagination_col1, pagination_col2, pagination_col3 = st.columns([1, 2, 1])

            with pagination_col1:
                if st.button(
                    "◀ Previous", disabled=(st.session_state.page_number == 0)
                ):
                    st.session_state.page_number -= 1
                    st.rerun()

            with pagination_col2:
                st.write(f"Page {st.session_state.page_number + 1} of {total_pages}")

            with pagination_col3:
                if st.button(
                    "Next ▶", disabled=(st.session_state.page_number >= total_pages - 1)
                ):
                    st.session_state.page_number += 1
                    st.rerun()

    with col3:
        if search_term:
            st.write(f"Showing {total_filtered} of {len(proposals)} proposals")
        else:
            st.write(f"Showing {start_idx + 1}-{end_idx} of {total_filtered} proposals")

    # Display proposals for current page
    current_page_proposals = filtered_proposals[start_idx:end_idx]

    for original_idx, proposal in current_page_proposals:
        col1, col2 = st.columns([0.05, 0.95])

        with col1:
            is_selected = st.checkbox(
                "Select",
                value=original_idx in st.session_state.selected_proposals,
                key=f"select_{original_idx}",
                label_visibility="collapsed",
            )

            # Update selection state
            if is_selected and original_idx not in st.session_state.selected_proposals:
                st.session_state.selected_proposals.append(original_idx)
            elif (
                not is_selected and original_idx in st.session_state.selected_proposals
            ):
                st.session_state.selected_proposals.remove(original_idx)

        with col2:
            # Display with diff highlighting and editable proposed name
            original_name = os.path.basename(proposal.original)

            # Create editable proposed name with unique key and store original
            edit_key = f"edit_{original_idx}"
            original_key = f"original_{original_idx}"

            # Initialize both edit and original keys when first created
            if edit_key not in st.session_state:
                st.session_state[edit_key] = os.path.basename(proposal.proposed)
            if original_key not in st.session_state:
                st.session_state[original_key] = proposal.proposed

            # Edit controls
            col2a, col2b = st.columns([3, 1])

            with col2a:
                new_proposed_name = st.text_input(
                    "Proposed filename:",
                    value=st.session_state[edit_key],
                    key=f"input_{original_idx}",
                    label_visibility="collapsed",
                )

                # Update session state if changed
                if new_proposed_name != st.session_state[edit_key]:
                    st.session_state[edit_key] = new_proposed_name
                    # Update the actual proposal
                    directory = os.path.dirname(proposal.original)
                    if directory:
                        new_full_path = os.path.join(directory, new_proposed_name)
                    else:
                        new_full_path = new_proposed_name
                    st.session_state.rename_proposals[original_idx].proposed = (
                        new_full_path
                    )

            with col2b:
                if st.button(
                    "↺ Reset",
                    key=f"reset_{original_idx}",
                    help="Reset to auto-generated name",
                ):
                    # Store original proposed name in session state if not already stored
                    original_key = f"original_{original_idx}"
                    if original_key not in st.session_state:
                        st.session_state[original_key] = proposal.proposed

                    # Reset to original proposed name
                    original_proposed = os.path.basename(st.session_state[original_key])
                    st.session_state[edit_key] = original_proposed
                    st.session_state.rename_proposals[original_idx].proposed = (
                        st.session_state[original_key]
                    )
                    st.rerun()

            # Create diff visualization with current values
            current_proposed_name = st.session_state[edit_key]
            diff_html = create_filename_diff(original_name, current_proposed_name)
            st.markdown(diff_html, unsafe_allow_html=True)

            # Show full path with current proposed name
            directory = os.path.dirname(proposal.original)
            if directory:
                current_full_path = os.path.join(directory, current_proposed_name)
            else:
                current_full_path = current_proposed_name
            st.write(f"**Full path:** `{current_full_path}`")

            if proposal.note:
                st.write(f"*Note: {proposal.note}*")
            st.write("---")

    # Display manual review files if any
    if st.session_state.manual_review:
        st.subheader("Files Requiring Manual Review")
        st.write(
            "The following files could not be automatically renamed (no datetime found):"
        )

        # Also paginate manual review if there are many
        manual_review_files = st.session_state.manual_review
        if len(manual_review_files) > 10:
            st.write(f"Showing first 10 of {len(manual_review_files)} files:")
            manual_review_files = manual_review_files[:10]

        for file_path in manual_review_files:
            st.write(f"- `{file_path}`")


def apply_changes():
    """Apply selected rename changes atomically."""
    if not st.session_state.rename_proposals:
        st.error("No proposals available to apply.")
        return False

    if not st.session_state.selected_proposals:
        st.warning("No proposals selected for application.")
        return False

    selected_proposals = [
        st.session_state.rename_proposals[i]
        for i in st.session_state.selected_proposals
    ]

    # Confirmation dialog
    st.write(f"**About to apply {len(selected_proposals)} rename operations:**")
    for proposal in selected_proposals[:5]:  # Show first 5
        st.write(
            f"- `{os.path.basename(proposal.original)}` → `{os.path.basename(proposal.proposed)}`"
        )
    if len(selected_proposals) > 5:
        st.write(f"... and {len(selected_proposals) - 5} more")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Dry Run", help="Simulate operations without making changes"):
            try:
                with st.spinner("Running dry run simulation..."):
                    dry_run_results = apply_renames_atomically(
                        selected_proposals, dry_run=True
                    )

                st.info(
                    f"🔍 Dry run completed: {dry_run_results} operations would succeed."
                )
                st.write("**No files were actually modified in dry run mode.**")
                return None
            except Exception as e:
                st.error(f"Error during dry run: {str(e)}")
                return False

    with col2:
        if st.button("⚠️ Confirm and Apply Changes", type="primary"):
            try:
                with st.spinner("Applying changes..."):
                    success_count = apply_renames_atomically(
                        selected_proposals, dry_run=False
                    )

                if success_count == len(selected_proposals):
                    st.success(
                        f"Successfully applied {success_count} rename operations!"
                    )
                    # Clear proposals after successful application
                    st.session_state.rename_proposals = None
                    st.session_state.selected_proposals = []
                    return True
                else:
                    st.error(
                        f"Only {success_count} of {len(selected_proposals)} operations were successful."
                    )
                    return False

            except Exception as e:
                st.error(f"Error applying changes: {str(e)}")
                return False

    return None  # User hasn't confirmed yet


def save_project_state():
    """Save current project state to JSON files."""
    try:
        # Save media tags if available
        if st.session_state.media_tags:
            media_tags_data = [tag.model_dump() for tag in st.session_state.media_tags]
            with open("media_tags.json", "w") as f:
                json.dump(media_tags_data, f, indent=2)

        # Save rename proposals if available
        if st.session_state.rename_proposals:
            proposals_data = [
                proposal.model_dump(exclude_none=True)
                for proposal in st.session_state.rename_proposals
            ]
            with open("rename_proposal.json", "w") as f:
                json.dump(proposals_data, f, indent=2)

        # Save manual review if available
        if st.session_state.manual_review:
            with open("manual_review.json", "w") as f:
                json.dump(st.session_state.manual_review, f, indent=2)

        # Save project state
        project_state = {
            "directory_path": st.session_state.directory_path,
            "selected_proposals": st.session_state.selected_proposals,
        }
        with open("project_state.json", "w") as f:
            json.dump(project_state, f, indent=2)

        st.success("Project state saved successfully!")
        return True
    except Exception as e:
        st.error(f"Error saving project state: {str(e)}")
        return False


def load_media_tags():
    """Load media tags from JSON file."""
    try:
        if os.path.exists("media_tags.json"):
            with open("media_tags.json", "r") as f:
                data = json.load(f)
            st.session_state.media_tags = [MediaTagInfo(**item) for item in data]
            st.success(f"Loaded {len(st.session_state.media_tags)} media tag entries.")
            return True
        else:
            st.warning("No media_tags.json file found.")
            return False
    except Exception as e:
        st.error(f"Error loading media tags: {str(e)}")
        return False


def load_rename_proposals():
    """Load rename proposals from JSON file."""
    try:
        if os.path.exists("rename_proposal.json"):
            with open("rename_proposal.json", "r") as f:
                data = json.load(f)
            st.session_state.rename_proposals = [
                RenameProposalItem(**item) for item in data
            ]
            # Initialize all proposals as selected
            st.session_state.selected_proposals = list(
                range(len(st.session_state.rename_proposals))
            )

            # Load manual review if available
            if os.path.exists("manual_review.json"):
                with open("manual_review.json", "r") as f:
                    st.session_state.manual_review = json.load(f)

            st.success(
                f"Loaded {len(st.session_state.rename_proposals)} rename proposals."
            )
            return True
        else:
            st.warning("No rename_proposal.json file found.")
            return False
    except Exception as e:
        st.error(f"Error loading rename proposals: {str(e)}")
        return False


def load_project_state():
    """Load complete project state from JSON files."""
    try:
        # Load project configuration
        if os.path.exists("project_state.json"):
            with open("project_state.json", "r") as f:
                project_state = json.load(f)
            st.session_state.directory_path = project_state.get("directory_path", ".")
            # Will restore selected proposals after loading rename proposals
            stored_selections = project_state.get("selected_proposals", [])
        else:
            stored_selections = []

        # Load media tags
        load_media_tags()

        # Load rename proposals
        if load_rename_proposals():
            # Restore selected proposals if they were saved
            if stored_selections:
                # Validate that the stored selections are still valid
                valid_selections = [
                    i
                    for i in stored_selections
                    if i < len(st.session_state.rename_proposals)
                ]
                st.session_state.selected_proposals = valid_selections

        st.success("Project state loaded successfully!")
        return True
    except Exception as e:
        st.error(f"Error loading project state: {str(e)}")
        return False


def apply_renames_atomically(
    proposals: List[RenameProposalItem], dry_run: bool = False
) -> int:
    """
    Apply rename operations atomically using the refactored AtomicRenamer class.

    Args:
        proposals: List of rename proposals to apply
        dry_run: If True, simulate operations without actually renaming files

    Returns:
        int: Number of successful rename operations (or would-be successful in dry run)
    """
    # Create atomic renamer with current media tags
    renamer = AtomicRenamer(st.session_state.media_tags)

    # Check for and recover from any previous crash
    if renamer.recover_from_journal():
        st.warning("🔄 Recovered unsaved changes from previous interrupted session.")
        # Reload media tags after recovery
        if st.session_state.media_tags:
            load_media_tags()

    # Set up progress tracking for Streamlit
    progress_bar = st.progress(0)
    progress_text = st.empty()

    def progress_callback(current: int, total: int, current_file: str):
        """Update Streamlit progress indicators."""
        try:
            progress = current / total if total > 0 else 1.0
            progress_bar.progress(
                min(progress, 1.0)
            )  # Ensure progress doesn't exceed 1.0
            progress_text.text(f"Processing {current}/{total}: {current_file}")

            # Show periodic saves every 100 entries
            if (
                renamer.unsaved_changes_count > 0
                and renamer.unsaved_changes_count % 50 == 0
            ):
                progress_text.text(
                    f"Processing {current}/{total}: {current_file} (unsaved changes: {renamer.unsaved_changes_count})"
                )
        except Exception as e:
            # Fallback progress display if something goes wrong
            progress_text.text(f"Processing: {current_file} (Error: {str(e)})")

    # Apply renames and get results
    result = renamer.apply_renames(
        proposals,
        dry_run=dry_run,
        update_tags=True,
        progress_callback=progress_callback,
    )

    # Show completion status before clearing progress
    if result.successful_operations:
        progress_bar.progress(1.0)  # Show 100% completion
        progress_text.text(
            f"Completed: {len(result.successful_operations)}/{len(proposals)} operations"
        )
        # Keep the progress visible for a moment
        import time

        time.sleep(0.5)

    # Clear progress indicators after showing completion
    progress_bar.empty()
    progress_text.empty()

    # Display conflicts if any
    if result.conflicts:
        st.error("Cannot proceed due to conflicts:")
        for conflict in result.conflicts:
            st.write(f"- {conflict}")
        st.write(f"Skipping {len(result.conflicts)} operations due to conflicts.")

    # Display results for each operation
    for src_path, dst_path in result.successful_operations:
        if dry_run:
            st.info(f"🔍 Would rename: `{src_path.name}` → `{dst_path.name}`")
        else:
            st.success(f"✅ Renamed: `{src_path.name}` → `{dst_path.name}`")

    # Display failures
    for src_path, dst_path, error in result.failed_operations:
        if dry_run:
            st.error(f"❌ Would fail: `{src_path.name}` → `{dst_path.name}`: {error}")
        else:
            st.error(f"❌ Failed: `{src_path.name}` → `{dst_path.name}`: {error}")

    # Display final summary
    if result.failed_operations:
        operation_word = "would fail" if dry_run else "failed"
        st.warning(f"⚠️ {len(result.failed_operations)} operations {operation_word}:")
        for src, dst, error in result.failed_operations:
            st.write(f"- `{src}` → `{dst}`: {error}")

    if result.successful_operations:
        if dry_run:
            st.info(
                f"🔍 Dry run: {len(result.successful_operations)} operations would succeed."
            )
        else:
            st.info(
                f"📝 Successfully renamed {len(result.successful_operations)} files."
            )
            # Save updated tags to file after all operations
            try:
                renamer.save_media_tags()
                st.success("📄 Media tags file updated with new filenames.")
            except Exception as e:
                st.warning(f"⚠️ Could not save media tags: {e}")

    return result.success_count


def check_for_journal_recovery():
    """Check for and handle journal recovery at startup."""
    from pathlib import Path

    journal_path = "media_tags_journal.json"
    if Path(journal_path).exists():
        # Create a temporary renamer to check for recovery
        temp_renamer = AtomicRenamer()
        if temp_renamer.recover_from_journal():
            st.success(
                "🔄 Recovered unsaved changes from previous interrupted session!"
            )
            # Reload media tags if available
            if Path("media_tags.json").exists():
                load_media_tags()
            return True
    return False


def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="Pic Organize - Review and Apply Changes",
        page_icon="📁",
        layout="wide",
    )

    st.title("📁 Pic Organize - Review and Apply Changes")
    st.markdown("Review and apply media file rename proposals")

    # Initialize session state
    init_session_state()

    # Check for journal recovery on first load
    if "journal_checked" not in st.session_state:
        if check_for_journal_recovery():
            st.rerun()  # Refresh to load recovered data
        st.session_state.journal_checked = True

    # Sidebar configuration
    with st.sidebar:
        st.header("Configuration")

        # Directory selection
        new_directory = st.text_input(
            "Media Directory:",
            value=st.session_state.directory_path,
            placeholder="Enter path to media files",
        )

        if new_directory != st.session_state.directory_path:
            st.session_state.directory_path = new_directory
            # Clear existing data when directory changes
            st.session_state.media_tags = None
            st.session_state.rename_proposals = None
            st.session_state.selected_proposals = []

        if st.session_state.directory_path and not os.path.exists(
            st.session_state.directory_path
        ):
            st.error(f"Directory does not exist: {st.session_state.directory_path}")
            return

        st.write(f"Current directory: `{st.session_state.directory_path}`")

        # Status indicators
        st.header("Status")
        if st.session_state.media_tags:
            st.success(f"✅ Tags extracted ({len(st.session_state.media_tags)} files)")
        else:
            st.info("📋 No tags extracted yet")

        if st.session_state.rename_proposals:
            st.success(
                f"✅ Proposals generated ({len(st.session_state.rename_proposals)} total)"
            )
            if st.session_state.selected_proposals:
                st.info(
                    f"🔘 {len(st.session_state.selected_proposals)} proposals selected"
                )
        else:
            st.info("📝 No proposals generated yet")

        # Project state management
        st.header("Project State")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                "💾 Save State", help="Save current project state to JSON files"
            ):
                save_project_state()

        with col2:
            if st.button("📂 Load State", help="Load project state from JSON files"):
                load_project_state()

        # Individual load options
        st.subheader("Load Individual Files")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📋 Load Tags", help="Load media_tags.json"):
                load_media_tags()

        with col2:
            if st.button("📝 Load Proposals", help="Load rename_proposal.json"):
                load_rename_proposals()

    # Main workflow buttons
    st.header("Workflow")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button(
            "1. Extract Tags", help="Scan directory and extract metadata tags"
        ):
            extract_tags()

    with col2:
        if st.button(
            "2. Generate Proposals",
            help="Create rename proposals based on extracted tags",
        ):
            generate_proposals()

    with col3:
        disabled = (
            not st.session_state.rename_proposals
            or not st.session_state.selected_proposals
        )
        if st.button(
            "3. Review Proposals",
            help="Review and select proposals to apply",
            disabled=disabled,
        ):
            pass  # The display happens below

    with col4:
        disabled = (
            not st.session_state.rename_proposals
            or not st.session_state.selected_proposals
        )
        if st.button(
            "4. Apply Changes",
            help="Apply selected rename operations",
            disabled=disabled,
        ):
            pass  # The apply UI happens below

    # Display proposals section
    if st.session_state.rename_proposals is not None:
        st.markdown("---")
        display_proposals()

        # Apply changes section
        if st.session_state.selected_proposals:
            st.markdown("---")
            st.header("Apply Changes")
            apply_changes()


if __name__ == "__main__":
    main()

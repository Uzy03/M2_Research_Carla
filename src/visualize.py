"""
2D Visualization module for CARLA trajectory data using mplsoccer pitch.
"""

import os
import h5py
import numpy as np
import matplotlib.pyplot as plt
from mplsoccer import Pitch


def plot_trajectories(h5_path: str, ax=None, title: str = None) -> plt.Figure:
    """
    Plot all actor trajectories from an h5 file on a custom mplsoccer pitch.
    
    Args:
        h5_path: Path to the h5 file
        ax: Matplotlib axes to draw on (if None, creates new figure)
        title: Title for the plot (if None, uses h5 filename)
    
    Returns:
        matplotlib.figure.Figure: The figure object
    """
    with h5py.File(h5_path, 'r') as f:
        actors_group = f['actors']
        
        # Collect all coordinates to determine pitch dimensions
        all_x = []
        all_y = []
        
        for actor_id in actors_group.keys():
            actor_group = actors_group[actor_id]
            if 'x' in actor_group and 'y' in actor_group:
                x = np.array(actor_group['x'][:])
                y = np.array(actor_group['y'][:])
                
                if len(x) > 0:
                    all_x.extend(x)
                    all_y.extend(y)
        
        if len(all_x) == 0:
            # No data to plot
            if ax is None:
                fig, ax = plt.subplots(figsize=(10, 10))
            else:
                fig = ax.get_figure()
            
            if title is None:
                title = os.path.basename(h5_path)
            ax.set_title(title)
            return fig
        
        # Calculate pitch dimensions with margin
        x_min, x_max = np.min(all_x), np.max(all_x)
        y_min, y_max = np.min(all_y), np.max(all_y)
        
        margin = 20
        pitch_length = x_max - x_min + 2 * margin
        pitch_width = y_max - y_min + 2 * margin
        
        # Create pitch with custom dimensions
        pitch = Pitch(
            pitch_type='custom',
            pitch_length=pitch_length,
            pitch_width=pitch_width,
            axis=ax,
            figsize=(10, 10)
        )
        
        if ax is None:
            fig, ax = pitch.draw()
        else:
            fig = ax.get_figure()
        
        # Plot trajectories for each actor
        for actor_id in actors_group.keys():
            actor_group = actors_group[actor_id]
            if 'x' in actor_group and 'y' in actor_group:
                x = np.array(actor_group['x'][:])
                y = np.array(actor_group['y'][:])
                
                if len(x) > 0:
                    ax.plot(x, y, alpha=0.6, linewidth=1.5)
        
        # Set title
        if title is None:
            title = os.path.basename(h5_path)
        ax.set_title(title)
    
    return fig


def visualize_batch(h5_paths: list, output_dir: str) -> None:
    """
    Visualize multiple h5 files and save them as PNG images.
    
    Args:
        h5_paths: List of paths to h5 files
        output_dir: Directory to save PNG files
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for h5_path in h5_paths:
        try:
            # Extract scenario ID from filename
            scenario_id = os.path.splitext(os.path.basename(h5_path))[0]
            
            # Plot trajectories
            fig = plot_trajectories(h5_path)
            
            # Save as PNG
            output_path = os.path.join(output_dir, f"{scenario_id}.png")
            fig.savefig(output_path, dpi=100, bbox_inches='tight')
            
            # Close figure to free memory
            plt.close(fig)
            
            print(f"Saved: {output_path}")
        except Exception as e:
            print(f"Error processing {h5_path}: {e}")


def compare_factual_counterfactual(
    factual_h5: str,
    counterfactual_h5: str,
    output_path: str = None
) -> plt.Figure:
    """
    Compare factual and counterfactual trajectories side by side.
    
    Args:
        factual_h5: Path to factual h5 file
        counterfactual_h5: Path to counterfactual h5 file
        output_path: Path to save the figure (if None, figure is not saved)
    
    Returns:
        matplotlib.figure.Figure: The figure object
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Plot factual on left
    plot_trajectories(factual_h5, ax=ax1, title="Factual")
    
    # Plot counterfactual on right
    plot_trajectories(counterfactual_h5, ax=ax2, title="Counterfactual")
    
    # Save if output path is specified
    if output_path is not None:
        fig.savefig(output_path, dpi=150, bbox_inches='tight')
    
    return fig

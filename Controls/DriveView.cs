using ReStoreX.Core;
using System;
using System.IO;
using System.Collections.Generic;
using System.Windows.Forms;

namespace ReStoreX.Controls
{
    /// <summary>
    /// DriveView control for ReStoreX file system navigation
    /// </summary>
    public partial class DriveView : UserControl
    {
        private IReStoreXFileSystem fileSystem = null!;
        private List<Volume> volumes = new List<Volume>();

        public event EventHandler<DirectoryEntry>? DirectorySelected;
        public event EventHandler<PartitionSelectedEventArgs>? TabSelectionChanged;

        public DriveView()
        {
            InitializeComponent();
            treeView1.AfterSelect += TreeView1_AfterSelect;
            partitionList.SelectedIndexChanged += PartitionList_SelectedIndexChanged;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        public void LoadFileSystem(IReStoreXFileSystem fs)
        {
            fileSystem = fs;
            PopulateTree();
        }

        private void PopulateTree()
        {
            treeView1.Nodes.Clear();
            var rootNode = new TreeNode($"{fileSystem.Name} ({FormatSize(fileSystem.TotalSpace - fileSystem.FreeSpace)} / {FormatSize(fileSystem.TotalSpace)})");
            
            foreach (var dir in fileSystem.GetDirectories("/"))
            {
                TreeNode node = CreateDirectoryNode(dir);
                rootNode.Nodes.Add(node);
            }
            
            treeView1.Nodes.Add(rootNode);
            rootNode.Expand();
        }

        private TreeNode CreateDirectoryNode(DirectoryEntry dir)
        {
            string nodeText = dir.DirectoryName;
            if (dir.Files.Count > 0)
            {
                nodeText += $" ({dir.Files.Count} files)";
            }
            
            TreeNode node = new TreeNode(nodeText);
            node.Tag = dir;  // Store the directory entry for later use
            
            foreach (var subDir in dir.SubDirectories)
            {
                TreeNode childNode = CreateDirectoryNode(subDir);
                node.Nodes.Add(childNode);
            }
            
            return node;
        }

        private string FormatSize(long bytes)
        {
            string[] sizes = { "B", "KB", "MB", "GB", "TB" };
            int order = 0;
            double size = bytes;
            
            while (size >= 1024 && order < sizes.Length - 1)
            {
                order++;
                size /= 1024;
            }
            
            return $"{size:0.##} {sizes[order]}";
        }

        private void TreeView1_AfterSelect(object? sender, TreeViewEventArgs e)
        {
            if (e.Node?.Tag is DirectoryEntry dir)
            {
                DirectorySelected?.Invoke(this, dir);
            }
        }

        public void AddDrive(string name, object disk)
        {
            var volume = new Volume
            {
                Mounted = true,
                Offset = 0,
                Length = 512 * 1024 * 1024 // 512 MB dummy size
            };
            volumes.Add(volume);
            partitionList.Items.Add($"{name} - Volume {volumes.Count}");
        }

        private void PartitionList_SelectedIndexChanged(object? sender, EventArgs e)
        {
            if (partitionList.SelectedIndex >= 0 && partitionList.SelectedIndex < volumes.Count)
            {
                TabSelectionChanged?.Invoke(this, new PartitionSelectedEventArgs(volumes[partitionList.SelectedIndex]));
            }
        }
    }
}

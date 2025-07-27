using ReStoreX.Core;
using System;
using System.IO;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Linq;
using ReStoreX.Utilities;

namespace ReStoreX.Controls
{
    /// <summary>
    /// DriveView control for ReStoreX file system navigation
    /// </summary>
    public partial class DriveView : UserControl
    {
        private IReStoreXFileSystem? fileSystem;
        private List<Volume> volumes = new List<Volume>();

        public IReStoreXFileSystem? FileSystem => fileSystem;

        public event EventHandler<DirectoryEntry>? DirectorySelected;
        public event EventHandler<PartitionSelectedEventArgs>? TabSelectionChanged;

        public DriveView()
        {
            InitializeComponent();
            treeView1.AfterSelect += TreeView1_AfterSelect;
            treeView1.BeforeExpand += TreeView1_BeforeExpand;
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
            if (fileSystem == null) return;

            treeView1.BeginUpdate();
            try
            {
                treeView1.Nodes.Clear();
                var rootNode = new TreeNode($"{fileSystem.Name} ({Utility.FormatFileSize(fileSystem.TotalSpace - fileSystem.FreeSpace)} / {Utility.FormatFileSize(fileSystem.TotalSpace)})") 
                { 
                    Tag = "/",
                    ImageKey = "folder",
                    SelectedImageKey = "folder"
                };
                
                // Add root node
                treeView1.Nodes.Add(rootNode);

                // Load initial directories
                foreach (var dir in fileSystem.GetDirectories("/"))
                {
                    TreeNode node = CreateDirectoryNode(dir);
                    rootNode.Nodes.Add(node);
                    
                    // Add a dummy node to show expand button
                    if (dir.Files.Count > 0 || fileSystem.GetDirectories(dir.DirectoryName).Any())
                    {
                        node.Nodes.Add(new TreeNode("Loading...") { Tag = "dummy" });
                    }
                }

                rootNode.Expand();
            }
            finally
            {
                treeView1.EndUpdate();
            }
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

        public void AddDrive(string name, IDisk disk)
        {
            var volume = new Volume(disk, name, 0, disk.Length);
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

        private void TreeView1_BeforeExpand(object? sender, TreeViewCancelEventArgs e)
        {
            if (e.Node == null || fileSystem == null) return;
            
            // Check if this node has only the dummy node
            if (e.Node.Nodes.Count == 1 && e.Node.Nodes[0].Tag?.ToString() == "dummy")
            {
                e.Node.Nodes.Clear();
                
                string path = e.Node.Tag is DirectoryEntry dir ? dir.DirectoryName : e.Node.Tag?.ToString() ?? "/";
                
                // Load subdirectories
                foreach (var subDir in fileSystem.GetDirectories(path))
                {
                    TreeNode node = CreateDirectoryNode(subDir);
                    e.Node.Nodes.Add(node);
                    
                    // Add a dummy node to show expand button if there are files or subdirectories
                    if (subDir.Files.Count > 0 || fileSystem.GetDirectories(subDir.DirectoryName).Any())
                    {
                        node.Nodes.Add(new TreeNode("Loading...") { Tag = "dummy" });
                    }
                }
            }
        }
    }
}

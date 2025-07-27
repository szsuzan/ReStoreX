using System;
using System.Drawing;
using System.Windows.Forms;
using System.IO;
using System.Threading.Tasks;
using System.Collections.Generic;
using System.Text;

namespace ReStoreX.Forms
{
    public partial class MainWindow : Form
    {
        private List<FileInfo> deletedFiles = new List<FileInfo>();
        private bool isScanning = false;

        public MainWindow()
        {
            InitializeComponent();
            InitializeEvents();
            LoadDrives();
            LoadSplitterPositions();
            
            // Add handlers to save splitter positions when moved
            // Save layout on form resize instead of splitter moves since we're using TableLayoutPanel
            this.ResizeEnd += (s, e) => SaveSplitterPositions();
        }

        private void InitializeEvents()
        {
            // Menu events
            var fileMenu = menuStrip.Items[0] as ToolStripMenuItem;
            var toolsMenu = menuStrip.Items[1] as ToolStripMenuItem;

            if (fileMenu != null)
            {
                var openMenu = fileMenu.DropDownItems[0] as ToolStripMenuItem;
                var scanMenu = fileMenu.DropDownItems[2] as ToolStripMenuItem;
                var exitMenu = fileMenu.DropDownItems[4] as ToolStripMenuItem;
                
                if (openMenu != null)
                    openMenu.Click += OpenMenu_Click;
                if (scanMenu != null)
                    scanMenu.Click += ScanMenu_Click;
                if (exitMenu != null)
                    exitMenu.Click += ExitMenu_Click;
            }

            if (toolsMenu != null)
            {
                var analyzeMenu = toolsMenu.DropDownItems[0] as ToolStripMenuItem;
                var hexViewMenu = toolsMenu.DropDownItems[1] as ToolStripMenuItem;

                if (analyzeMenu != null)
                    analyzeMenu.Click += AnalyzeMenu_Click;
                if (hexViewMenu != null)
                    hexViewMenu.Click += HexViewMenu_Click;
            }

            // TreeView events
            driveTreeView.AfterSelect += DriveTreeView_AfterSelect;
            driveTreeView.BeforeExpand += DriveTreeView_BeforeExpand;

            // ListView events
            fileListView.SelectedIndexChanged += FileListView_SelectedIndexChanged;
            fileListView.MouseDoubleClick += FileListView_MouseDoubleClick;

            // Button events
            scanButton.Click += ScanButton_Click;
            recoverButton.Click += RecoverButton_Click;

            // Form events
            this.FormClosing += MainWindow_FormClosing;
        }

        private void LoadDrives()
        {
            try
            {
                driveTreeView.BeginUpdate();
                driveTreeView.Nodes.Clear();
                
                foreach (DriveInfo drive in DriveInfo.GetDrives())
                {
                    try
                    {
                        if (drive.IsReady)
                        {
                            string driveLabel = string.IsNullOrEmpty(drive.VolumeLabel) 
                                ? drive.Name 
                                : $"{drive.VolumeLabel} ({drive.Name})";
                            
                            var node = new TreeNode(driveLabel);
                            node.Tag = drive.RootDirectory;
                            node.Nodes.Add(new TreeNode("Loading..."));
                            driveTreeView.Nodes.Add(node);
                        }
                    }
                    catch (UnauthorizedAccessException)
                    {
                        // Skip drives we can't access
                        continue;
                    }
                }

                if (driveTreeView.Nodes.Count > 0)
                {
                    driveTreeView.SelectedNode = driveTreeView.Nodes[0];
                }
                
                UpdateStatus("Drives loaded successfully");
            }
            catch (Exception ex)
            {
                UpdateStatus($"Error loading drives: {ex.Message}", true);
            }
            finally
            {
                driveTreeView.EndUpdate();
            }
        }

        private void LoadDirectory(TreeNode node)
        {
            try
            {
                if (node.Tag is DirectoryInfo dir)
                {
                    node.Nodes.Clear();
                    foreach (DirectoryInfo subDir in dir.GetDirectories())
                    {
                        var subNode = new TreeNode(subDir.Name);
                        subNode.Tag = subDir;
                        subNode.Nodes.Add(new TreeNode("Loading..."));
                        node.Nodes.Add(subNode);
                    }
                }
            }
            catch (Exception ex)
            {
                UpdateStatus($"Error loading directory: {ex.Message}", true);
            }
        }

        private void LoadFiles(DirectoryInfo directory)
        {
            try
            {
                fileListView.Items.Clear();
                foreach (FileInfo file in directory.GetFiles())
                {
                    var item = fileListView.Items.Add(file.Name);
                    item.SubItems.AddRange(new string[] {
                        FormatFileSize(file.Length),
                        file.Extension,
                        file.LastWriteTime.ToString()
                    });
                    item.Tag = file;
                }
                UpdateStatus($"Loaded {fileListView.Items.Count} files");
            }
            catch (Exception ex)
            {
                UpdateStatus($"Error loading files: {ex.Message}", true);
            }
        }

        private string FormatFileSize(long bytes)
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

        private void UpdateStatus(string message, bool isError = false)
        {
            statusLabel.Text = message;
            statusLabel.ForeColor = isError ? Color.Red : SystemColors.ControlText;
        }

        #region Event Handlers

        private void OpenMenu_Click(object? sender, EventArgs e)
        {
            LoadDrives();
        }

        private void ExitMenu_Click(object? sender, EventArgs e)
        {
            Close();
        }

        private void DriveTreeView_BeforeExpand(object? sender, TreeViewCancelEventArgs e)
        {
            if (e.Node?.Nodes.Count == 1 && e.Node.Nodes[0].Text == "Loading...")
            {
                LoadDirectory(e.Node);
            }
        }

        private void DriveTreeView_AfterSelect(object? sender, TreeViewEventArgs e)
        {
            if (e.Node?.Tag is DirectoryInfo dir)
            {
                LoadFiles(dir);
            }
        }

        private void MainWindow_FormClosing(object? sender, FormClosingEventArgs e)
        {
            if (isScanning)
            {
                if (MessageBox.Show("A scan is in progress. Are you sure you want to exit?", "Confirm Exit",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Warning) == DialogResult.No)
                {
                    e.Cancel = true;
                    return;
                }
            }
            else if (MessageBox.Show("Are you sure you want to exit?", "Confirm Exit",
                MessageBoxButtons.YesNo, MessageBoxIcon.Question) == DialogResult.No)
            {
                e.Cancel = true;
            }
        }

        private void FileListView_SelectedIndexChanged(object? sender, EventArgs e)
        {
            bool hasSelection = fileListView.SelectedItems.Count > 0;
            recoverButton.Enabled = hasSelection;

            if (hasSelection)
            {
                var file = fileListView.SelectedItems[0].Tag as FileInfo;
                if (file != null)
                {
                    filePropertyGrid.SelectedObject = file;
                }
            }
            else
            {
                filePropertyGrid.SelectedObject = null;
            }
        }

        private void FileListView_MouseDoubleClick(object? sender, MouseEventArgs e)
        {
            if (fileListView.SelectedItems.Count > 0)
            {
                AnalyzeSelectedFile();
            }
        }

        private void ScanButton_Click(object? sender, EventArgs e)
        {
            StartScan();
        }

        private void ScanMenu_Click(object? sender, EventArgs e)
        {
            StartScan();
        }

        private void RecoverButton_Click(object? sender, EventArgs e)
        {
            RecoverSelectedFile();
        }

        private void AnalyzeMenu_Click(object? sender, EventArgs e)
        {
            AnalyzeSelectedFile();
        }

        private void HexViewMenu_Click(object? sender, EventArgs e)
        {
            ShowHexView();
        }

        private async void StartScan()
        {
            if (driveTreeView.SelectedNode?.Tag is not DirectoryInfo currentDir)
            {
                MessageBox.Show("Please select a directory to scan.", "No Directory Selected",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            if (isScanning)
            {
                MessageBox.Show("A scan is already in progress.", "Scan in Progress",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            try
            {
                isScanning = true;
                scanButton.Enabled = false;
                scanProgressBar.Visible = true;
                scanProgressBar.Style = ProgressBarStyle.Marquee;
                UpdateStatus("Scanning for deleted files...");

                deletedFiles.Clear();
                await Task.Run(() => ScanForDeletedFiles(currentDir));

                fileListView.Items.Clear();
                foreach (var file in deletedFiles)
                {
                    var item = fileListView.Items.Add(file.Name);
                    item.SubItems.AddRange(new string[] {
                        FormatFileSize(file.Length),
                        file.Extension,
                        file.LastWriteTime.ToString()
                    });
                    item.Tag = file;
                }

                UpdateStatus($"Found {deletedFiles.Count} deleted files");
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error during scan: {ex.Message}", "Scan Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                UpdateStatus("Scan failed", true);
            }
            finally
            {
                isScanning = false;
                scanButton.Enabled = true;
                scanProgressBar.Visible = false;
            }
        }

        private void ScanForDeletedFiles(DirectoryInfo directory)
        {
            try
            {
                // This is a placeholder for actual file recovery logic
                // In a real implementation, this would:
                // 1. Read raw disk sectors
                // 2. Look for file signatures
                // 3. Analyze file system structures
                // 4. Identify deleted file entries
                
                // For now, we'll just simulate finding some deleted files
                Random rand = new Random();
                int numFiles = rand.Next(5, 15);
                
                for (int i = 0; i < numFiles; i++)
                {
                    var mockFile = new FileInfo(Path.Combine(directory.FullName, $"DELETED_FILE_{i}.dat"));
                    deletedFiles.Add(mockFile);
                }
            }
            catch (Exception ex)
            {
                throw new Exception($"Error scanning directory {directory.FullName}: {ex.Message}");
            }
        }

        private void RecoverSelectedFile()
        {
            if (fileListView.SelectedItems.Count == 0)
                return;

            var file = fileListView.SelectedItems[0].Tag as FileInfo;
            if (file == null)
                return;

            using (SaveFileDialog dialog = new SaveFileDialog())
            {
                dialog.FileName = file.Name;
                dialog.Filter = "All files (*.*)|*.*";

                if (dialog.ShowDialog() == DialogResult.OK)
                {
                    try
                    {
                        // This is a placeholder for actual file recovery logic
                        UpdateStatus($"Recovering {file.Name}...");
                        
                        // Simulate recovery by creating an empty file
                        File.WriteAllBytes(dialog.FileName, new byte[file.Length]);
                        
                        UpdateStatus($"Successfully recovered {file.Name}");
                        MessageBox.Show("File recovered successfully!", "Recovery Complete",
                            MessageBoxButtons.OK, MessageBoxIcon.Information);
                    }
                    catch (Exception ex)
                    {
                        UpdateStatus("Recovery failed", true);
                        MessageBox.Show($"Error recovering file: {ex.Message}", "Recovery Error",
                            MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                }
            }
        }

        private void AnalyzeSelectedFile()
        {
            if (fileListView.SelectedItems.Count == 0)
                return;

            var file = fileListView.SelectedItems[0].Tag as FileInfo;
            if (file == null)
                return;

            filePropertyGrid.SelectedObject = file;
            detailsTabControl.SelectedTab = fileInfoTab;
        }

        private void ShowHexView()
        {
            if (fileListView.SelectedItems.Count == 0)
                return;

            var file = fileListView.SelectedItems[0].Tag as FileInfo;
            if (file == null)
                return;

            try
            {
                // This is a placeholder for actual hex viewing logic
                // In a real implementation, this would read the raw bytes from disk
                hexViewer.Clear();
                
                // Create a mock hex dump
                StringBuilder hexDump = new StringBuilder();
                Random rand = new Random();
                byte[] mockData = new byte[256];
                rand.NextBytes(mockData);

                for (int i = 0; i < mockData.Length; i += 16)
                {
                    // Offset
                    hexDump.AppendFormat("{0:X8}: ", i);

                    // Hex values
                    for (int j = 0; j < 16; j++)
                    {
                        if (i + j < mockData.Length)
                            hexDump.AppendFormat("{0:X2} ", mockData[i + j]);
                        else
                            hexDump.Append("   ");
                    }

                    hexDump.Append(" ");

                    // ASCII representation
                    for (int j = 0; j < 16 && i + j < mockData.Length; j++)
                    {
                        char c = (char)mockData[i + j];
                        hexDump.Append(char.IsControl(c) ? '.' : c);
                    }

                    hexDump.AppendLine();
                }

                hexViewer.Text = hexDump.ToString();
                detailsTabControl.SelectedTab = hexViewTab;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Error viewing file: {ex.Message}", "View Error",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        #endregion
    }
}

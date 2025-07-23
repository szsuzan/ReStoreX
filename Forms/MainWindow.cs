using System;
using System.IO;
using System.Security.Principal;
using System.Text;
using System.Windows.Forms;
using Microsoft.Win32.SafeHandles;
using ReStoreX.Controls;
using ReStoreX.Core;
using ReStoreX.Dialogs;
using ReStoreX.DiskTypes;
using ReStoreX.Utilities;

namespace ReStoreX.Forms
{
    public partial class MainWindow : Form
    {
        private DriveView driveView = null!;
        private const string ApplicationTitle = "ReStoreX";

        // Folder explorer fields
        private Panel nativeExplorerPanel = null!;
        private SplitContainer nativeSplit = null!;
        private TreeView nativeTree = null!;
        private ListView nativeList = null!;
        private ContextMenuStrip nativeListCtx = null!;
        private ToolStripMenuItem nativeOpenMenuItem = null!;
        private ToolStripMenuItem nativeCopyMenuItem = null!;
        private ToolStripMenuItem nativeDeleteMenuItem = null!;

        private string currentRootPath = string.Empty;
        private string currentSelectedFolder = string.Empty;
        private ToolStripMenuItem openFolderToolStripMenuItem = null!;

        private void DisableDatabaseOptions()
        {
            // TODO: Implement when database features are added
        }

        public MainWindow()
        {
            InitializeComponent();
            this.Text = ApplicationTitle;
            DisableDatabaseOptions();
            Console.SetOut(new LogWriter(this.textBox1));
            Console.WriteLine("--------------------------------");
            Console.WriteLine("ReStoreX");
            Console.WriteLine("--------------------------------");

            InitializeNativeExplorerUI();
            AddOpenFolderMenuItem();
            ShowNativeExplorer(false); 
        }

        #region LogWriter
        public class LogWriter : TextWriter
        {
            private readonly TextBox textBox;
            private delegate void SafeCallDelegate(string? text);
            public LogWriter(TextBox textBox) { this.textBox = textBox; }

            public override void Write(char value) { textBox.Text += value; }
            public override void Write(string? value) { textBox.AppendText(value ?? string.Empty); }
            public override void WriteLine() { textBox.AppendText(NewLine); }
            public override void WriteLine(string? value)
            {
                if (textBox.InvokeRequired)
                {
                    var d = new SafeCallDelegate(WriteLine);
                    textBox.BeginInvoke(d, new object?[] { value });
                }
                else { textBox.AppendText((value ?? string.Empty) + NewLine); }
            }
            public override Encoding Encoding => Encoding.ASCII;
        }
        #endregion

        // ================== UI Mode ==================
        private void ShowDriveView(bool show)
        {
            if (driveView != null) driveView.Visible = show;
            if (show) ShowNativeExplorer(false);
        }

        private void ShowNativeExplorer(bool show)
        {
            if (nativeExplorerPanel != null) nativeExplorerPanel.Visible = show;
            if (show && driveView != null) driveView.Visible = false;
        }

        private bool InNativeExplorerMode => nativeExplorerPanel?.Visible ?? false;

        // ================= FATX/NTFS Disk =================
        private void CreateNewDriveView(string path)
        {
            this.Text = $"{ApplicationTitle} - {Path.GetFileName(path)}";
            ShowNativeExplorer(false);

            splitContainer1.Panel1.Controls.Remove(driveView);
            driveView = new DriveView
            {
                Dock = DockStyle.Fill
            };
            driveView.TabSelectionChanged += DriveView_TabSelectionChanged;
            splitContainer1.Panel1.Controls.Add(driveView);
            ShowDriveView(true);
        }

        private void DriveView_TabSelectionChanged(object? sender, PartitionSelectedEventArgs e)
        {
            statusStrip1.Items.Clear();
            if (e?.volume == null) return;

            var volume = e.volume;
            if (volume.Mounted)
            {
                var used = volume.GetUsedSpace();
                var free = volume.GetFreeSpace();
                var total = volume.GetTotalSpace();
                statusStrip1.Items.Add($"Volume Offset: 0x{volume.Offset:X}");
                statusStrip1.Items.Add($"Volume Length: 0x{volume.Length:X}");
                statusStrip1.Items.Add($"Used: {Utility.FormatFileSize(used)}");
                statusStrip1.Items.Add($"Free: {Utility.FormatFileSize(free)}");
                statusStrip1.Items.Add($"Total: {Utility.FormatFileSize(total)}");
            }
        }

        private void OpenDiskImage(string path)
        {
            CreateNewDriveView(path);
            RawImage rawImage = new RawImage(path);
            driveView.AddDrive(Path.GetFileName(path), rawImage);
        }

        private void OpenDisk(string device)
        {
            CreateNewDriveView(device);
            SafeFileHandle handle = WinApi.CreateFile(device, FileAccess.Read, FileShare.ReadWrite, IntPtr.Zero, FileMode.Open, 0, IntPtr.Zero);
            long length = WinApi.GetDiskCapactity(handle);
            long sector = WinApi.GetSectorSize(handle);
            PhysicalDisk disk = new PhysicalDisk(handle, length, sector);
            driveView.AddDrive(device, disk);
        }

        private void openImageToolStripMenuItem_Click(object sender, EventArgs e)
        {
            OpenFileDialog ofd = new OpenFileDialog();
            if (ofd.ShowDialog() == DialogResult.OK)
                OpenDiskImage(ofd.FileName);
        }

        private void openDeviceToolStripMenuItem_Click(object? sender, EventArgs e)
        {
            bool isAdmin = new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator);
            if (!isAdmin)
            {
                MessageBox.Show("Run as Administrator to access devices.", "Access Denied");
                return;
            }
            using var ds = new DeviceSelectionDialog();
            if (ds.ShowDialog() == DialogResult.OK && ds.SelectedDevice != null)
            {
                OpenDisk(ds.SelectedDevice);
            }
        }

        // ================== Native Folder Explorer ==================
        private void AddOpenFolderMenuItem()
        {
            openFolderToolStripMenuItem = new ToolStripMenuItem("Open Folder...", null, openFolderToolStripMenuItem_Click);
            fileToolStripMenuItem.DropDownItems.Insert(0, openFolderToolStripMenuItem);
        }

        private void openFolderToolStripMenuItem_Click(object? sender, EventArgs e)
        {
            using var fbd = new FolderBrowserDialog();
            if (fbd.ShowDialog() == DialogResult.OK && !string.IsNullOrEmpty(fbd.SelectedPath))
            {
                OpenFolder(fbd.SelectedPath);
            }
        }

        private void OpenFolder(string path)
        {
            if (!Directory.Exists(path))
            {
                MessageBox.Show("Invalid folder path");
                return;
            }

            currentRootPath = path;
            currentSelectedFolder = path;
            this.Text = $"{ApplicationTitle} - {path}";

            PopulateNativeTreeFromDirectory(path);
            PopulateNativeListView(path);
            ShowNativeExplorer(true);
        }

        private void InitializeNativeExplorerUI()
        {
            nativeExplorerPanel = new Panel { Dock = DockStyle.Fill, Visible = false };
            nativeSplit = new SplitContainer { Dock = DockStyle.Fill, SplitterDistance = 250 };

            nativeTree = new TreeView { Dock = DockStyle.Fill };
            nativeTree.AfterSelect += NativeTree_AfterSelect;

            nativeList = new ListView { Dock = DockStyle.Fill, View = View.Details, FullRowSelect = true };
            nativeList.Columns.Add("Name", 200);
            nativeList.Columns.Add("Size", 100);
            nativeList.Columns.Add("Modified", 150);
            nativeList.DoubleClick += NativeList_DoubleClick;

            nativeListCtx = new ContextMenuStrip();
            nativeOpenMenuItem = new ToolStripMenuItem("Open", null, NativeOpenMenuItem_Click);
            nativeCopyMenuItem = new ToolStripMenuItem("Copy", null, NativeCopyMenuItem_Click);
            nativeDeleteMenuItem = new ToolStripMenuItem("Delete", null, NativeDeleteMenuItem_Click);
            nativeListCtx.Items.AddRange(new[] { nativeOpenMenuItem, nativeCopyMenuItem, nativeDeleteMenuItem });
            nativeList.ContextMenuStrip = nativeListCtx;

            nativeSplit.Panel1.Controls.Add(nativeTree);
            nativeSplit.Panel2.Controls.Add(nativeList);
            nativeExplorerPanel.Controls.Add(nativeSplit);
            splitContainer1.Panel1.Controls.Add(nativeExplorerPanel);
        }

        private void PopulateNativeTreeFromDirectory(string rootPath)
        {
            nativeTree.Nodes.Clear();
            var root = new TreeNode(rootPath) { Tag = rootPath };
            nativeTree.Nodes.Add(root);
            LoadNativeDirectories(root, rootPath);
        }

        private void LoadNativeDirectories(TreeNode parent, string path)
        {
            parent.Nodes.Clear();
            try
            {
                foreach (var dir in Directory.GetDirectories(path))
                {
                    var node = new TreeNode(Path.GetFileName(dir)) { Tag = dir };
                    parent.Nodes.Add(node);
                }
            }
            catch { }
        }

        private void PopulateNativeListView(string directory)
        {
            nativeList.Items.Clear();
            try
            {
                foreach (var dir in Directory.GetDirectories(directory))
                {
                    DirectoryInfo di = new DirectoryInfo(dir);
                    var item = new ListViewItem(new[] { di.Name, "<DIR>", di.LastWriteTime.ToString() }) { Tag = dir };
                    nativeList.Items.Add(item);
                }

                foreach (var file in Directory.GetFiles(directory))
                {
                    FileInfo fi = new FileInfo(file);
                    var item = new ListViewItem(new[] { fi.Name, $"{fi.Length / 1024} KB", fi.LastWriteTime.ToString() }) { Tag = file };
                    nativeList.Items.Add(item);
                }
            }
            catch { }
        }

        private void NativeTree_AfterSelect(object? sender, TreeViewEventArgs e)
        {
            if (e?.Node?.Tag is string path && Directory.Exists(path))
            {
                currentSelectedFolder = path;
                PopulateNativeListView(path);
            }
        }

        private void NativeList_DoubleClick(object? sender, EventArgs e)
        {
            if (nativeList.SelectedItems.Count == 0) return;
            if (nativeList.SelectedItems[0].Tag is string path)
            {
                if (Directory.Exists(path))
                    PopulateNativeListView(path);
                else if (File.Exists(path))
                    NativeOpenFile(path);
            }
        }

        private void NativeOpenMenuItem_Click(object? sender, EventArgs e)
        {
            if (nativeList.SelectedItems.Count == 0) return;
            if (nativeList.SelectedItems[0].Tag is string path)
            {
                if (Directory.Exists(path))
                    PopulateNativeListView(path);
                else if (File.Exists(path))
                    NativeOpenFile(path);
            }
        }

        private void NativeCopyMenuItem_Click(object? sender, EventArgs e)
        {
            if (nativeList.SelectedItems.Count == 0) return;
            if (nativeList.SelectedItems[0].Tag is string filePath && File.Exists(filePath))
            {
                using var sfd = new SaveFileDialog { FileName = Path.GetFileName(filePath) };
                if (sfd.ShowDialog() == DialogResult.OK)
                {
                    File.Copy(filePath, sfd.FileName, true);
                }
            }
        }

        private void NativeDeleteMenuItem_Click(object? sender, EventArgs e)
        {
            if (nativeList.SelectedItems.Count == 0) return;
            if (nativeList.SelectedItems[0].Tag is string filePath)
            {
                if (MessageBox.Show($"Delete {Path.GetFileName(filePath)}?", "Confirm", MessageBoxButtons.YesNo) == DialogResult.Yes)
                {
                    File.Delete(filePath);
                }
            }
        }

        private void NativeOpenFile(string filePath)
        {
            try { System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo { FileName = filePath, UseShellExecute = true }); }
            catch (Exception ex) { MessageBox.Show($"Cannot open file: {ex.Message}"); }
        }

        private void exitToolStripMenuItem_Click(object? sender, EventArgs e)
        {
            Close();
        }
    }
}

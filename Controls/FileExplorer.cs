using ReStoreX.Core;
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Drawing;
using System.Windows.Forms;
using System.ComponentModel;
using System.Threading.Tasks;

namespace ReStoreX.Controls
{
    public partial class FileExplorer : UserControl
    {
        private IReStoreXFileSystem fileSystem = null!;
        private string currentDirectory = "/";
        private bool showDeletedFiles = false;

        public FileExplorer()
        {
            InitializeComponent();
            SetupListView();
        }

        public IReStoreXFileSystem FileSystem => fileSystem;
        
        public string CurrentDirectory
        {
            get => currentDirectory;
            set
            {
                if (currentDirectory != value)
                {
                    currentDirectory = value;
                    if (fileSystem != null)
                    {
                        PopulateFiles();
                    }
                }
            }
        }

        public FileEntry? SelectedFile
        {
            get
            {
                if (listView1.SelectedItems.Count == 0)
                    return null;
                return listView1.SelectedItems[0].Tag as FileEntry;
            }
        }

        public void ShowDeletedFiles(bool show)
        {
            showDeletedFiles = show;
            PopulateFiles();
        }



        private void SetupListView()
        {
            listView1.Columns.Add("Name", 200);
            listView1.Columns.Add("Size", 100);
            listView1.Columns.Add("Created", 120);
            listView1.Columns.Add("Modified", 120);
            listView1.Columns.Add("Attributes", 100);
            listView1.Columns.Add("Status", 100);

            listView1.ContextMenuStrip = new ContextMenuStrip();
            listView1.ContextMenuStrip.Items.Add("Recover File", null, RecoverFile_Click);
            listView1.ContextMenuStrip.Items.Add("Scan for Deleted Files", null, ScanDeletedFiles_Click);
            listView1.ContextMenuStrip.Items.Add("View File Details", null, ViewFileDetails_Click);
        }

        public void LoadFileSystem(IReStoreXFileSystem fs)
        {
            fileSystem = fs;
            PopulateFiles();
        }

        internal void PopulateFiles()
        {
            listView1.Items.Clear();
            
            var files = showDeletedFiles ? 
                fileSystem.ScanForDeletedFiles() : 
                fileSystem.GetFiles(currentDirectory).Select(f => new DeletedFileEntry 
                { 
                    FileName = f.FileName,
                    FileSize = f.FileSize,
                    CreationTime = f.CreationTime,
                    LastWriteTime = f.LastWriteTime,
                    Attributes = f.Attributes,
                    RecoveryStatus = FileRecoveryStatus.Recoverable
                });

            foreach (var file in files)
            {
                var item = new ListViewItem(file.FileName);
                item.SubItems.Add(FormatSize(file.FileSize));
                item.SubItems.Add(file.CreationTime.ToString("g"));
                item.SubItems.Add(file.LastWriteTime.ToString("g"));
                item.SubItems.Add(file.Attributes.ToString());
                item.SubItems.Add(file.RecoveryStatus.ToString());
                
                if (file.IsCorrupted)
                {
                    item.ForeColor = Color.Red;
                    item.ToolTipText = file.ErrorMessage;
                }
                
                item.Tag = file;
                listView1.Items.Add(item);
            }
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

        private async void RecoverFile_Click(object? sender, EventArgs e)
        {
            if (listView1.SelectedItems.Count == 0) return;
            
            if (listView1.SelectedItems[0].Tag is DeletedFileEntry file)
            {
                using var dialog = new SaveFileDialog();
                dialog.FileName = file.FileName;
                
                if (dialog.ShowDialog() == DialogResult.OK)
                {
                    bool success = await Task.Run(() => fileSystem.RecoverFile(file, dialog.FileName));
                    MessageBox.Show(
                        success ? "File recovered successfully!" : 
                                "Failed to recover file. The file might be corrupted or overwritten.",
                        "File Recovery",
                        MessageBoxButtons.OK,
                        success ? MessageBoxIcon.Information : MessageBoxIcon.Error);
                }
            }
        }

        private void ScanDeletedFiles_Click(object? sender, EventArgs e)
        {
            showDeletedFiles = !showDeletedFiles;
            PopulateFiles();
        }

        private void ViewFileDetails_Click(object? sender, EventArgs e)
        {
            if (listView1.SelectedItems.Count == 0) return;
            
            if (listView1.SelectedItems[0].Tag is DeletedFileEntry file)
            {
                var details = new StringBuilder();
                details.AppendLine($"File: {file.FileName}");
                details.AppendLine($"Size: {FormatSize(file.FileSize)}");
                details.AppendLine($"Created: {file.CreationTime}");
                details.AppendLine($"Modified: {file.LastWriteTime}");
                details.AppendLine($"Attributes: {file.Attributes}");
                details.AppendLine($"Recovery Status: {file.RecoveryStatus}");
                
                if (file.RecoveryStatus == FileRecoveryStatus.Fragmented)
                {
                    details.AppendLine($"Fragments: {file.FragmentedClusters.Count}");
                }
                
                if (file.SignatureType != null)
                {
                    details.AppendLine($"File Type: {file.SignatureType}");
                }
                
                MessageBox.Show(
                    details.ToString(), 
                    "File Details", 
                    MessageBoxButtons.OK, 
                    MessageBoxIcon.Information
                );
            }
        }
    }
}

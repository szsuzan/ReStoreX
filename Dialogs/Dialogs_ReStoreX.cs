using ReStoreX.Core;
using System;
using System.Windows.Forms;

namespace ReStoreX.Dialogs
{
    public partial class FileInfoDialog : Form
    {
        public FileInfoDialog(IReStoreXFileSystem fs, FileEntry file)
        {
            InitializeComponent();

            listView1.Items.Add("Name").SubItems.Add(file.FileName);
            listView1.Items.Add("Size in bytes").SubItems.Add(file.FileSize.ToString());
            listView1.Items.Add("First Cluster").SubItems.Add(file.FirstCluster.ToString());
            listView1.Items.Add("Attributes").SubItems.Add("N/A");

            listView1.Items.Add("Creation Time").SubItems.Add(file.CreationTime.ToString());
            listView1.Items.Add("Last Write Time").SubItems.Add(file.LastWriteTime.ToString());
            listView1.Items.Add("Last Access Time").SubItems.Add(file.LastAccessTime.ToString());
        }
    }

    public partial class ClusterChainDialog : Form
    {
        private IReStoreXFileSystem currentFileSystem;
        private FileEntry currentFile;

        public ClusterChainDialog(IReStoreXFileSystem fs, FileEntry file)
        {
            InitializeComponent();
            currentFileSystem = fs;
            currentFile = file;
            PopulateClusters();
        }

        private void PopulateClusters()
        {
            // TODO: Populate cluster data (future: map FATX cluster chain here)
            listView1.Items.Clear();
            listView1.Items.Add(new ListViewItem(new[] {"Cluster 0x00", "Index 0"}));
        }
    }
}

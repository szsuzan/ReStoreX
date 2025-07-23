using System;
using System.IO;
using System.Windows.Forms;

namespace ReStoreX.Dialogs
{
    public partial class Partition_Device_Dialogs_ReStoreX : Form
    {
        private string selectedDevice = string.Empty;

        public Partition_Device_Dialogs_ReStoreX()
        {
            InitializeComponent();
            LoadDrives();
        }

        /// <summary>
        /// Populates the ListView with all available drives.
        /// </summary>
        private void LoadDrives()
        {
            listView1.Clear();
            listView1.View = View.Details;
            listView1.Columns.Add("Drive", 100);
            listView1.Columns.Add("Label", 120);
            listView1.Columns.Add("Type", 100);
            listView1.Columns.Add("File System", 100);
            listView1.Columns.Add("Total Size", 120);

            foreach (DriveInfo drive in DriveInfo.GetDrives())
            {
                try
                {
                    if (!drive.IsReady) continue;

                    string driveName = drive.Name;
                    string volumeLabel = drive.VolumeLabel;
                    string driveType = drive.DriveType.ToString();
                    string fileSystem = drive.DriveFormat;
                    string totalSize = $"{drive.TotalSize / (1024 * 1024 * 1024)} GB";

                    ListViewItem item = new ListViewItem(new[] {
                        driveName,
                        volumeLabel,
                        driveType,
                        fileSystem,
                        totalSize
                    });

                    listView1.Items.Add(item);
                }
                catch
                {
                    // Ignore drives we cannot access.
                }
            }

            listView1.FullRowSelect = true;
            listView1.SelectedIndexChanged += ListView1_SelectedIndexChanged;
            listView1.DoubleClick += (s, e) => { this.DialogResult = DialogResult.OK; this.Close(); };
        }

        private void ListView1_SelectedIndexChanged(object? sender, EventArgs e)
        {
            if (listView1.SelectedItems.Count > 0)
            {
                selectedDevice = listView1.SelectedItems[0].Text; // Drive letter like "C:\"
            }
        }

        /// <summary>
        /// Returns the selected drive path.
        /// </summary>
        public string GetSelectedDevice()
        {
            return selectedDevice;
        }
    }
}

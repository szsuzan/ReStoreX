using ReStoreX.Core;
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Drawing;
using System.Windows.Forms;
using System.Threading.Tasks;

namespace ReStoreX.Controls
{
    public class FileRecoveryUI : Form
    {
        private readonly DriveView driveView;
        private readonly FileExplorer fileExplorer;
        private readonly StatusStrip statusStrip;
        private readonly ToolStripStatusLabel statusLabel;
        private readonly ToolStripProgressBar progressBar;

        public FileRecoveryUI()
        {
            Text = "ReStoreX - Data Recovery";
            Size = new Size(1024, 768);

            // Create layout
            var splitContainer = new SplitContainer
            {
                Dock = DockStyle.Fill,
                SplitterDistance = 250
            };

            driveView = new DriveView { Dock = DockStyle.Fill };
            fileExplorer = new FileExplorer { Dock = DockStyle.Fill };
            
            splitContainer.Panel1.Controls.Add(driveView);
            splitContainer.Panel2.Controls.Add(fileExplorer);

            // Create status bar
            statusStrip = new StatusStrip();
            statusLabel = new ToolStripStatusLabel();
            progressBar = new ToolStripProgressBar();
            
            statusStrip.Items.AddRange(new ToolStripItem[] { statusLabel, progressBar });
            progressBar.Visible = false;

            Controls.AddRange(new Control[] { splitContainer, statusStrip });

            // Wire up events
            driveView.DirectorySelected += DriveView_DirectorySelected;
        }

        private void DriveView_DirectorySelected(object? sender, DirectoryEntry e)
        {
            if (fileExplorer.FileSystem != null)
            {
                fileExplorer.CurrentDirectory = e.DirectoryName;
                fileExplorer.PopulateFiles();
            }
        }

        public void LoadFileSystem(IReStoreXFileSystem fs)
        {
            driveView.LoadFileSystem(fs);
            fileExplorer.LoadFileSystem(fs);
            
            var health = fs.GetDiskHealth();
            UpdateDiskHealthStatus(health);
        }

        private void UpdateDiskHealthStatus(DiskHealthInfo health)
        {
            string status = $"Disk Health: {health.Status} | Model: {health.Model} | Temperature: {health.Temperature}°C";
            
            if (health.Status == DiskHealthStatus.Critical)
            {
                status += " | WARNING: Disk health is critical!";
                statusLabel.ForeColor = Color.Red;
            }
            else if (health.Status == DiskHealthStatus.Warning)
            {
                status += " | CAUTION: Disk health needs attention";
                statusLabel.ForeColor = Color.Orange;
            }
            
            statusLabel.Text = status;
        }

        public void StartDiskOperation(string operation)
        {
            progressBar.Visible = true;
            statusLabel.Text = $"Operation in progress: {operation}";
        }

        public void UpdateProgress(int percentage)
        {
            progressBar.Value = percentage;
        }

        public void EndDiskOperation()
        {
            progressBar.Visible = false;
            progressBar.Value = 0;
        }
    }
}

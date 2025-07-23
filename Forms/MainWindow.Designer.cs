using System.Windows.Forms;

namespace ReStoreX.Forms
{
    partial class MainWindow
    {
        private MenuStrip menuStrip1;
        private ToolStripMenuItem fileToolStripMenuItem;
        private ToolStripMenuItem openImageToolStripMenuItem;
        private ToolStripMenuItem openDeviceToolStripMenuItem;
        private ToolStripMenuItem exitToolStripMenuItem;
        private StatusStrip statusStrip1;
        private SplitContainer splitContainer1;
        private TextBox textBox1;

        private void InitializeComponent()
        {
            this.menuStrip1 = new MenuStrip();
            this.fileToolStripMenuItem = new ToolStripMenuItem();
            this.openImageToolStripMenuItem = new ToolStripMenuItem();
            this.openDeviceToolStripMenuItem = new ToolStripMenuItem();
            this.exitToolStripMenuItem = new ToolStripMenuItem();
            this.statusStrip1 = new StatusStrip();
            this.splitContainer1 = new SplitContainer();
            this.textBox1 = new TextBox();

            // MenuStrip
            this.fileToolStripMenuItem.Text = "File";
            this.openImageToolStripMenuItem.Text = "Open Image...";
            this.openDeviceToolStripMenuItem.Text = "Open Device...";
            this.exitToolStripMenuItem.Text = "Exit";

            this.openImageToolStripMenuItem.Click += openImageToolStripMenuItem_Click;
            this.openDeviceToolStripMenuItem.Click += openDeviceToolStripMenuItem_Click;
            this.exitToolStripMenuItem.Click += exitToolStripMenuItem_Click;

            this.fileToolStripMenuItem.DropDownItems.AddRange(new ToolStripItem[]
            {
                openImageToolStripMenuItem,
                openDeviceToolStripMenuItem,
                exitToolStripMenuItem
            });
            this.menuStrip1.Items.Add(fileToolStripMenuItem);

            // SplitContainer
            this.splitContainer1.Dock = DockStyle.Fill;
            this.splitContainer1.Orientation = Orientation.Horizontal;
            this.splitContainer1.SplitterDistance = 400;
            this.splitContainer1.Panel2.Controls.Add(this.textBox1);

            // TextBox
            this.textBox1.Dock = DockStyle.Fill;
            this.textBox1.Multiline = true;
            this.textBox1.ScrollBars = ScrollBars.Vertical;

            // MainWindow
            this.Controls.Add(this.splitContainer1);
            this.Controls.Add(this.statusStrip1);
            this.Controls.Add(this.menuStrip1);
            this.MainMenuStrip = this.menuStrip1;
            this.Text = "ReStoreX";
            this.WindowState = FormWindowState.Maximized;
        }
    }
}

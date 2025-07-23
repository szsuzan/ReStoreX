namespace ReStoreX.Dialogs
{
    partial class FileInfoDialog
    {
        private System.ComponentModel.IContainer components = null;
        private System.Windows.Forms.ListView listView1;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.listView1 = new System.Windows.Forms.ListView();
            this.SuspendLayout();
            // 
            // listView1
            // 
            this.listView1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.listView1.Location = new System.Drawing.Point(0, 0);
            this.listView1.Name = "listView1";
            this.listView1.Size = new System.Drawing.Size(400, 300);
            this.listView1.TabIndex = 0;
            this.listView1.View = System.Windows.Forms.View.Details;
            // 
            // FileInfoDialog
            // 
            this.ClientSize = new System.Drawing.Size(400, 300);
            this.Controls.Add(this.listView1);
            this.Name = "FileInfoDialog";
            this.Text = "File Info";
            this.ResumeLayout(false);
        }
    }

    partial class ClusterChainDialog
    {
        private System.ComponentModel.IContainer components = null;
        private System.Windows.Forms.ListView listView1;

        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        private void InitializeComponent()
        {
            this.listView1 = new System.Windows.Forms.ListView();
            this.SuspendLayout();
            // 
            // listView1
            // 
            this.listView1.Dock = System.Windows.Forms.DockStyle.Fill;
            this.listView1.Location = new System.Drawing.Point(0, 0);
            this.listView1.Name = "listView1";
            this.listView1.Size = new System.Drawing.Size(400, 300);
            this.listView1.TabIndex = 0;
            this.listView1.View = System.Windows.Forms.View.Details;
            // 
            // ClusterChainDialog
            // 
            this.ClientSize = new System.Drawing.Size(400, 300);
            this.Controls.Add(this.listView1);
            this.Name = "ClusterChainDialog";
            this.Text = "Cluster Chain";
            this.ResumeLayout(false);
        }
    }
}

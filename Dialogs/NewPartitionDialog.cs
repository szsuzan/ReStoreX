using System;
using System.Windows.Forms;

namespace ReStoreX.Dialogs
{
    public partial class NewPartitionDialog : Form
    {
#pragma warning disable CS8618 // Non-nullable field must contain a non-null value when exiting constructor
        public NewPartitionDialog()
#pragma warning restore CS8618
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.label1 = new System.Windows.Forms.Label();
            this.button1 = new System.Windows.Forms.Button();
            this.SuspendLayout();
            // 
            // label1
            // 
            this.label1.AutoSize = true;
            this.label1.Location = new System.Drawing.Point(12, 9);
            this.label1.Name = "label1";
            this.label1.Size = new System.Drawing.Size(150, 17);
            this.label1.TabIndex = 0;
            this.label1.Text = "Create a new partition";
            // 
            // button1
            // 
            this.button1.Location = new System.Drawing.Point(15, 40);
            this.button1.Name = "button1";
            this.button1.Size = new System.Drawing.Size(75, 23);
            this.button1.TabIndex = 1;
            this.button1.Text = "OK";
            this.button1.UseVisualStyleBackColor = true;
            this.button1.Click += new System.EventHandler(this.Button1_Click);
            // 
            // NewPartitionDialog
            // 
            this.ClientSize = new System.Drawing.Size(200, 100);
            this.Controls.Add(this.button1);
            this.Controls.Add(this.label1);
            this.Name = "NewPartitionDialog";
            this.Text = "New Partition";
            this.ResumeLayout(false);
            this.PerformLayout();
        }

        private void Button1_Click(object? sender, EventArgs e)
        {
            this.DialogResult = DialogResult.OK;
            this.Close();
        }

        private System.Windows.Forms.Label label1;
        private System.Windows.Forms.Button button1;
    }
}

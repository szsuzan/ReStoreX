using System;
using System.Collections.Generic;
using System.Windows.Forms;
using ReStoreX.Core;
using ReStoreX.Utilities;

namespace ReStoreX.Dialogs
{
    public partial class DeviceSelectionDialog : Form
    {
        private ListViewItem? selectedItem;

#pragma warning disable CS8618 // Non-nullable field must contain a non-null value when exiting constructor
        public DeviceSelectionDialog()
#pragma warning restore CS8618
        {
            InitializeComponent();
            LoadDevices();
        }

        private void LoadDevices()
        {
            listView1.Items.Clear();
            var disks = WinApi.GetAvailablePhysicalDrives();
            foreach (var disk in disks)
            {
                var item = new ListViewItem(disk);
                listView1.Items.Add(item);
            }
        }

        public string? SelectedDevice => selectedItem?.Text;

        private void listView1_SelectedIndexChanged(object? sender, EventArgs e)
        {
            selectedItem = listView1.SelectedItems.Count > 0 ? listView1.SelectedItems[0] : null;
            btnOK.Enabled = selectedItem != null;
        }

        private void btnOK_Click(object? sender, EventArgs e)
        {
            DialogResult = DialogResult.OK;
            Close();
        }

        private void btnCancel_Click(object? sender, EventArgs e)
        {
            DialogResult = DialogResult.Cancel;
            Close();
        }

        private void InitializeComponent()
        {
            listView1 = new ListView();
            btnOK = new Button();
            btnCancel = new Button();
            SuspendLayout();
            // 
            // listView1
            // 
            listView1.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Bottom;
            listView1.Location = new Point(12, 12);
            listView1.Name = "listView1";
            listView1.Size = new Size(460, 198);
            listView1.TabIndex = 0;
            listView1.UseCompatibleStateImageBehavior = false;
            listView1.View = View.Details;
            listView1.SelectedIndexChanged += listView1_SelectedIndexChanged;
            // 
            // btnOK
            // 
            btnOK.Anchor = AnchorStyles.Bottom | AnchorStyles.Right;
            btnOK.DialogResult = DialogResult.OK;
            btnOK.Enabled = false;
            btnOK.Location = new Point(316, 226);
            btnOK.Name = "btnOK";
            btnOK.Size = new Size(75, 23);
            btnOK.TabIndex = 1;
            btnOK.Text = "OK";
            btnOK.Click += btnOK_Click;
            // 
            // btnCancel
            // 
            btnCancel.Anchor = AnchorStyles.Bottom | AnchorStyles.Right;
            btnCancel.DialogResult = DialogResult.Cancel;
            btnCancel.Location = new Point(397, 226);
            btnCancel.Name = "btnCancel";
            btnCancel.Size = new Size(75, 23);
            btnCancel.TabIndex = 2;
            btnCancel.Text = "Cancel";
            btnCancel.Click += btnCancel_Click;
            // 
            // DeviceSelectionDialog
            // 
            AcceptButton = btnOK;
            CancelButton = btnCancel;
            ClientSize = new Size(484, 261);
            Controls.Add(btnCancel);
            Controls.Add(btnOK);
            Controls.Add(listView1);
            MinimizeBox = false;
            Name = "DeviceSelectionDialog";
            ShowIcon = false;
            StartPosition = FormStartPosition.CenterParent;
            Text = "Select Physical Drive";
            ResumeLayout(false);
        }

        private ListView listView1;
        private Button btnOK;
        private Button btnCancel;
    }
}

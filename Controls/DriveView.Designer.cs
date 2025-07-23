#nullable enable

using System;
using System.Windows.Forms;

namespace ReStoreX.Controls
{
    partial class DriveView
    {
        private System.ComponentModel.IContainer? components;
        private TreeView treeView1 = null!;
        private ListBox partitionList = null!;

        private void InitializeComponent()
        {
            components = new System.ComponentModel.Container();
            partitionList = new ListBox();
            treeView1 = new TreeView();
            SuspendLayout();
            // 
            // partitionList
            // 
            partitionList.Dock = DockStyle.Left;
            partitionList.Location = new System.Drawing.Point(0, 0);
            partitionList.Name = "partitionList";
            partitionList.Size = new System.Drawing.Size(200, 150);
            partitionList.TabIndex = 0;
            partitionList.SelectedIndexChanged += PartitionList_SelectedIndexChanged;
            // 
            // treeView1
            // 
            treeView1.Dock = DockStyle.Fill;
            treeView1.Location = new System.Drawing.Point(200, 0);
            treeView1.Name = "treeView1";
            treeView1.Size = new System.Drawing.Size(400, 150);
            treeView1.TabIndex = 1;
            treeView1.AfterSelect += TreeView1_AfterSelect;
            // 
            // DriveView
            // 
            AutoScaleDimensions = new System.Drawing.SizeF(7F, 15F);
            AutoScaleMode = AutoScaleMode.Font;
            Controls.Add(treeView1);
            Controls.Add(partitionList);
            Name = "DriveView";
            Size = new System.Drawing.Size(600, 150);
            ResumeLayout(false);
        }
    }
}

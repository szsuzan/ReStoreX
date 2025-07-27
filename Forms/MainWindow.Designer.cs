using System;
using System.ComponentModel;
using System.Drawing;
using System.Windows.Forms;
using System.IO;

namespace ReStoreX.Forms
{
    partial class MainWindow
    {
        private IContainer components = null;
        private const string SETTINGS_FILE = "layout.config";

        // UI Components
        private MenuStrip menuStrip;
        private StatusStrip statusStrip;
        private ToolStripStatusLabel statusLabel;
        private SplitContainer mainSplitContainer;
        private TreeView driveTreeView;
        private ListView fileListView;
        private Panel bottomPanel;
        private Button scanButton;
        private Button recoverButton;
        private ProgressBar scanProgressBar;
        private TabControl detailsTabControl;
        private TabPage fileInfoTab;
        private TabPage hexViewTab;
        private PropertyGrid filePropertyGrid;
        private RichTextBox hexViewer;

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
            this.components = new Container();

            // Initialize all components
            InitializeMainComponents();
            InitializeMenuStrip();
            InitializeMainLayout();
            InitializeStatusStrip();

            // Configure form
            this.MinimumSize = new Size(800, 600);
            this.Size = new Size(1024, 768);
            this.Text = "ReStoreX - Data Recovery Tool";
        }

        private void InitializeMainComponents()
        {
            this.menuStrip = new MenuStrip();
            this.statusStrip = new StatusStrip();
            this.statusLabel = new ToolStripStatusLabel();
            this.mainSplitContainer = new SplitContainer();
            this.driveTreeView = new TreeView();
            this.fileListView = new ListView();
            this.bottomPanel = new Panel();
            this.scanButton = new Button();
            this.recoverButton = new Button();
            this.scanProgressBar = new ProgressBar();
            this.detailsTabControl = new TabControl();
            this.fileInfoTab = new TabPage();
            this.hexViewTab = new TabPage();
            this.filePropertyGrid = new PropertyGrid();
            this.hexViewer = new RichTextBox();
        }

        private void InitializeMenuStrip()
        {
            // File Menu
            var fileMenu = new ToolStripMenuItem("&File");
            var openMenu = new ToolStripMenuItem("&Open Drive...");
            var scanMenu = new ToolStripMenuItem("&Scan for Deleted Files");
            var exitMenu = new ToolStripMenuItem("E&xit");
            fileMenu.DropDownItems.AddRange(new ToolStripItem[] {
                openMenu,
                new ToolStripSeparator(),
                scanMenu,
                new ToolStripSeparator(),
                exitMenu
            });

            // Tools Menu
            var toolsMenu = new ToolStripMenuItem("&Tools");
            var analyzeMenu = new ToolStripMenuItem("&Analyze File");
            var hexViewMenu = new ToolStripMenuItem("&Hex View");
            toolsMenu.DropDownItems.AddRange(new ToolStripItem[] { analyzeMenu, hexViewMenu });

            // Help Menu
            var helpMenu = new ToolStripMenuItem("&Help");
            var aboutMenu = new ToolStripMenuItem("&About");
            helpMenu.DropDownItems.Add(aboutMenu);

            this.menuStrip.Items.AddRange(new ToolStripItem[] { fileMenu, toolsMenu, helpMenu });
            this.menuStrip.Dock = DockStyle.Top;
            this.Controls.Add(this.menuStrip);
        }

        private void InitializeMainLayout()
        {
            // Main container spanning the whole form
            var mainContainer = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 1,
                ColumnCount = 2,
                Padding = new Padding(3),
                BackColor = SystemColors.Control
            };

            mainContainer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 200F));  // Drive tree width
            mainContainer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));   // Rest of the space

            // Configure drive tree
            this.driveTreeView.Dock = DockStyle.Fill;
            this.driveTreeView.ShowLines = true;
            this.driveTreeView.ShowPlusMinus = true;
            this.driveTreeView.ShowRootLines = true;
            this.driveTreeView.HideSelection = false;
            this.driveTreeView.BorderStyle = BorderStyle.FixedSingle;

            // Right side container
            var rightContainer = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                RowCount = 2,
                ColumnCount = 1,
                Margin = new Padding(3, 0, 0, 0)
            };

            rightContainer.RowStyles.Add(new RowStyle(SizeType.Percent, 70F));    // File list gets 70%
            rightContainer.RowStyles.Add(new RowStyle(SizeType.Percent, 30F));    // Bottom panel gets 30%

            // Configure file list
            this.fileListView.Dock = DockStyle.Fill;
            this.fileListView.View = View.Details;
            this.fileListView.FullRowSelect = true;
            this.fileListView.GridLines = true;
            this.fileListView.BorderStyle = BorderStyle.FixedSingle;
            this.fileListView.Columns.AddRange(new ColumnHeader[]
            {
                new ColumnHeader { Text = "Name", Width = 200 },
                new ColumnHeader { Text = "Size", Width = 100 },
                new ColumnHeader { Text = "Type", Width = 100 },
                new ColumnHeader { Text = "Date Modified", Width = 150 }
            });

            // Configure bottom panel
            this.bottomPanel.Dock = DockStyle.Fill;
            this.bottomPanel.BorderStyle = BorderStyle.FixedSingle;
            this.bottomPanel.Padding = new Padding(5);

            // Configure tabs
            this.detailsTabControl.Dock = DockStyle.Fill;
            
            this.fileInfoTab.Text = "File Info";
            this.fileInfoTab.Controls.Add(this.filePropertyGrid);
            this.filePropertyGrid.Dock = DockStyle.Fill;
            
            this.hexViewTab.Text = "Hex View";
            this.hexViewTab.Controls.Add(this.hexViewer);
            this.hexViewer.Dock = DockStyle.Fill;
            this.hexViewer.Font = new Font("Consolas", 9F);
            this.hexViewer.ReadOnly = true;
            this.hexViewer.WordWrap = false;

            this.detailsTabControl.TabPages.Add(this.fileInfoTab);
            this.detailsTabControl.TabPages.Add(this.hexViewTab);

            // Configure buttons panel
            var buttonPanel = new FlowLayoutPanel
            {
                Dock = DockStyle.Top,
                Height = 40,
                Padding = new Padding(0, 5, 0, 5),
                FlowDirection = FlowDirection.LeftToRight
            };

            this.scanButton.Text = "Scan for Deleted Files";
            this.scanButton.Width = 150;
            this.scanButton.Height = 30;
            this.scanButton.Margin = new Padding(0, 0, 5, 0);

            this.recoverButton.Text = "Recover Selected";
            this.recoverButton.Width = 120;
            this.recoverButton.Height = 30;
            this.recoverButton.Enabled = false;

            this.scanProgressBar.Width = 200;
            this.scanProgressBar.Height = 30;
            this.scanProgressBar.Margin = new Padding(10, 0, 0, 0);
            this.scanProgressBar.Style = ProgressBarStyle.Continuous;

            buttonPanel.Controls.AddRange(new Control[] { this.scanButton, this.recoverButton, this.scanProgressBar });

            // Assemble bottom panel
            this.bottomPanel.Controls.Add(this.detailsTabControl);
            this.bottomPanel.Controls.Add(buttonPanel);

            // Assemble right container
            rightContainer.Controls.Add(this.fileListView, 0, 0);
            rightContainer.Controls.Add(this.bottomPanel, 0, 1);

            // Assemble main container
            mainContainer.Controls.Add(this.driveTreeView, 0, 0);
            mainContainer.Controls.Add(rightContainer, 1, 0);

            this.Controls.Add(mainContainer);
        }

        private void InitializeStatusStrip()
        {
            this.statusLabel.Text = "Ready";
            this.statusStrip.Items.Add(this.statusLabel);
            this.statusStrip.Dock = DockStyle.Bottom;
            this.Controls.Add(this.statusStrip);
        }

        private void SaveSplitterPositions()
        {
            try
            {
                var settings = new StringWriter();
                settings.WriteLine(this.Width);
                settings.WriteLine(this.Height);
                // Store the layout percentages instead of pixel values
                var mainContainer = (TableLayoutPanel)this.Controls[2]; // Skip menustrip and statusstrip
                var rightContainer = (TableLayoutPanel)mainContainer.Controls[1];
                settings.WriteLine(mainContainer.ColumnStyles[0].Width);  // Drive tree width
                settings.WriteLine(rightContainer.RowStyles[0].Height);   // File list height percentage
                File.WriteAllText(SETTINGS_FILE, settings.ToString());
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to save layout: {ex.Message}");
            }
        }

        private void LoadSplitterPositions()
        {
            try
            {
                if (File.Exists(SETTINGS_FILE))
                {
                    var lines = File.ReadAllLines(SETTINGS_FILE);
                    if (lines.Length >= 4)
                    {
                        if (int.TryParse(lines[0], out int width))
                            this.Width = Math.Max(this.MinimumSize.Width, width);
                        if (int.TryParse(lines[1], out int height))
                            this.Height = Math.Max(this.MinimumSize.Height, height);
                            
                        // Restore layout percentages
                        var mainContainer = (TableLayoutPanel)this.Controls[2]; // Skip menustrip and statusstrip
                        var rightContainer = (TableLayoutPanel)mainContainer.Controls[1];
                        
                        if (float.TryParse(lines[2], out float driveTreeWidth))
                            mainContainer.ColumnStyles[0].Width = driveTreeWidth;
                        if (float.TryParse(lines[3], out float fileListHeight))
                            rightContainer.RowStyles[0].Height = fileListHeight;
                    }
                }
            }
            catch (Exception ex)
            {
                System.Diagnostics.Debug.WriteLine($"Failed to load layout: {ex.Message}");
            }
        }
    }
}

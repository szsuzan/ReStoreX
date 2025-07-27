using System;
using System.Drawing;
using System.Windows.Forms;

namespace ReStoreX
{
    public class TestForm : Form
    {
        public TestForm()
        {
            this.Text = "Test Form";
            this.Size = new Size(400, 300);
            this.StartPosition = FormStartPosition.CenterScreen;
            
            var button = new Button
            {
                Text = "Click Me",
                Location = new Point(150, 100),
                Size = new Size(100, 30)
            };
            button.Click += (s, e) => MessageBox.Show("Button clicked!");
            
            this.Controls.Add(button);
        }
    }
}

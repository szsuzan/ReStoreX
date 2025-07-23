using System;
using System.Windows.Forms;
using ReStoreX.Forms;

namespace ReStoreX
{
    internal static class Program
    {
        /// <summary>
        /// The main entry point for the application.
        /// </summary>
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // Launch MainWindow
            Application.Run(new MainWindow());
        }
    }
}

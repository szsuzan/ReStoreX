using System;
using System.Windows.Forms;
using ReStoreX;
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
            ApplicationConfiguration.Initialize();

            // Create and run the main form
            var mainForm = new MainWindow();
            Application.Run(mainForm);
        }
    }
}

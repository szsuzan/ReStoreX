using ReStoreX.Core;
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Drawing;
using System.Windows.Forms;
using System.ComponentModel;
using System.Threading.Tasks;

namespace ReStoreX.Controls
{
    /// <summary>
    /// Base class for custom controls in ReStoreX
    /// </summary>
    public abstract class Controls_ReStoreX : UserControl
    {
        protected string FormatSize(long bytes)
        {
            string[] sizes = { "B", "KB", "MB", "GB", "TB" };
            int order = 0;
            double size = bytes;
            
            while (size >= 1024 && order < sizes.Length - 1)
            {
                order++;
                size /= 1024;
            }
            
            return $"{size:0.##} {sizes[order]}";
        }
    }


}

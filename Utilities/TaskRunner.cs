using System;
using System.Threading.Tasks;

namespace ReStoreX.Utilities
{
    public static class TaskRunner
    {
        /// <summary>
        /// Runs an action asynchronously.
        /// </summary>
        public static void Run(Action action)
        {
            Task.Run(action);
        }

        /// <summary>
        /// Runs an asynchronous function with error handling.
        /// </summary>
        public static async Task RunAsync(Func<Task> action)
        {
            try
            {
                await action();
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error: " + ex.Message);
            }
        }
    }
}

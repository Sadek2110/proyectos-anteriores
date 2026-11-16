<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Datos del formulario</title>
</head>
<body>
    <h1>Datos recibidos del formulario</h1>

    <?php
    if ($_SERVER["REQUEST_METHOD"] == "POST") {

        echo "<h2>Información Personal</h2>";
        echo "<p><strong>Género:</strong> " . ($_POST["genero"] ?? "No especificado") . "</p>";
        echo "<p><strong>Nombre:</strong> " . ($_POST["nombre"] ?? "") . "</p>";
        echo "<p><strong>Apellido:</strong> " . ($_POST["apellido"] ?? "") . "</p>";
        echo "<p><strong>Fecha de nacimiento:</strong> " . ($_POST["f_nac"] ?? "") . "</p>";
        echo "<p><strong>Ciudad:</strong> " . ($_POST["ciudad"] ?? "") . "</p>";
        echo "<p><strong>Región:</strong> " . ($_POST["region"] ?? "") . "</p>";
        echo "<p><strong>Código Postal:</strong> " . ($_POST["c_postal"] ?? "") . "</p>";
        echo "<p><strong>Código Regional:</strong> " . ($_POST["c_reg"] ?? "") . "</p>";

        echo "<h2>Información de Suscripción</h2>";
        echo "<p><strong>Tipo de suscripción:</strong> " . ($_POST["t_suscripcion"] ?? "") . "</p>";
        echo "<p><strong>Código de suscripción:</strong> " . ($_POST["c_suscripcion"] ?? "") . "</p>";

        echo "<h3>Intereses personales:</h3>";
        if (!empty($_POST["intereses"])) {
            echo "<ul>";
            foreach ($_POST["intereses"] as $interes) {
                echo "<li>$interes</li>";
            }
            echo "</ul>";
        } else {
            echo "<p>No seleccionó intereses.</p>";
        }

        echo "<h2>Datos de usuario</h2>";
        echo "<p><strong>Nombre de usuario:</strong> " . ($_POST["nombre_usuario"] ?? "") . "</p>";
        echo "<p><strong>Contraseña:</strong> " . ($_POST["contrasena"] ?? "") . "</p>";

        echo "<h2>Información de cobro</h2>";
        echo "<p><strong>Tipo de tarjeta:</strong> " . ($_POST["t_tarjeta"] ?? "") . "</p>";
        echo "<p><strong>Número de tarjeta:</strong> " . ($_POST["n_tarjeta"] ?? "") . "</p>";
        echo "<p><strong>Código de descuento:</strong> " . ($_POST["descuento"] ?? "Ninguno") . "</p>";

        echo "<h2>Feedback</h2>";
        echo "<p><strong>Sugerencias:</strong> " . nl2br($_POST["sugerencias"] ?? "") . "</p>";

    } else {
        echo "<p>No se han recibido datos.</p>";
    }
    ?>

</body>
</html>

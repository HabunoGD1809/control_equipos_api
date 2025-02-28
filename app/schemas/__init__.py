from app.schemas.common import (
    ErrorResponse, ItemCreatedResponse, ItemDeletedResponse, 
    ItemResponse, ItemsResponse, ItemUpdatedResponse, 
    Mensaje, PaginacionParams, PaginatedResponse, SearchParams
)
from app.schemas.token import (
    LoginRequest, PasswordResetConfirm, PasswordResetRequest, Token, TokenPayload
)
from app.schemas.usuarios import (
    LoginLog, LoginLogBase, LoginLogCreate,
    Notificacion, NotificacionBase, NotificacionCreate,
    Permiso, PermisoBase, PermisoCreate, PermisoUpdate,
    Rol, RolBase, RolCreate, RolUpdate,
    Usuario, UsuarioBase, UsuarioChangePassword, UsuarioCreate, UsuarioInDB, UsuarioUpdate
)
from app.schemas.equipos import (
    Documentacion, DocumentacionBase, DocumentacionConUsuarios, DocumentacionCreate, 
    DocumentacionUpdate, DocumentacionVerificar,
    Equipo, EquipoBase, EquipoBusqueda, EquipoConRelaciones, EquipoCreate, EquipoUpdate,
    EstadoEquipo, EstadoEquipoBase, EstadoEquipoCreate, EstadoEquipoUpdate,
    Proveedor, ProveedorBase, ProveedorCreate, ProveedorUpdate,
    TipoDocumento, TipoDocumentoBase, TipoDocumentoCreate, TipoDocumentoUpdate
)
from app.schemas.movimientos import (
    Movimiento, MovimientoAutorizar, MovimientoBase, MovimientoCancelar, 
    MovimientoConDetalles, MovimientoCreate, MovimientoRetorno, MovimientoUpdate
)
from app.schemas.mantenimiento import (
    Mantenimiento, MantenimientoBase, MantenimientoConDetalles, MantenimientoCreate, 
    MantenimientoEstado, MantenimientoUpdate,
    TipoMantenimiento, TipoMantenimientoBase, TipoMantenimientoCreate, TipoMantenimientoUpdate
)
